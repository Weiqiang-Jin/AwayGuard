"""Bounded Windows Security queries. No shell and no policy mutations."""
import subprocess
import xml.etree.ElementTree as ET

NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
KINDS = {4800: "系统锁屏", 4801: "系统解锁", 4624: "交互式登录成功", 4625: "交互式登录失败", 1102: "安全日志已清空"}
FILTER = "(EventID=4800 or EventID=4801 or EventID=4624 or EventID=4625 or EventID=1102)"


def parse_events(xml):
    root = ET.fromstring(xml)
    results = []
    for event in root.findall("e:Event", NS):
        system = event.find("e:System", NS)
        event_id = int(system.findtext("e:EventID", namespaces=NS))
        record = int(system.findtext("e:EventRecordID", namespaces=NS))
        timestamp = system.find("e:TimeCreated", NS).attrib["SystemTime"]
        data = {item.attrib.get("Name"): item.text or "" for item in event.findall("e:EventData/e:Data", NS)}
        results.append({"event_id": event_id, "record_id": record, "time": timestamp, "data": data})
    return results


def query(xpath="*", newest=False, count=200):
    command = ["wevtutil.exe", "qe", "Security", "/q:" + xpath, "/f:xml", "/e:Events",
               "/rd:" + str(newest).lower(), "/c:" + str(count), "/uni:true"]
    result = subprocess.run(command, capture_output=True, timeout=12,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    # /uni:true produces UTF-16LE, including redirected output.
    output = result.stdout.decode("utf-16", errors="replace").lstrip("\ufeff")
    if result.returncode:
        raise RuntimeError("无法读取 Security 日志（错误码 %s）。请以管理员身份运行，并检查系统审计策略。" % result.returncode)
    return parse_events(output) if output.strip() else []


def public_event(event):
    data = event["data"]
    event_id = event["event_id"]
    if event_id not in KINDS:
        return None
    if event_id in (4624, 4625) and data.get("LogonType") not in ("2", "7", "10", "11", "12", "13"):
        return None  # Ignore service, batch and network authentication noise.
    allowed = ("TargetUserName", "TargetDomainName", "LogonType", "SessionId", "Status", "SubStatus")
    details = {key: data[key] for key in allowed if key in data}
    details.update(event_id=event_id, record_id=event["record_id"], scope="本机所有会话")
    return KINDS[event_id], details, event["time"]


class EventReader:
    def __init__(self):
        self.cursor = None

    def poll(self):
        latest = query(newest=True, count=1)
        newest = latest[0]["record_id"] if latest else 0
        if self.cursor is None:
            self.cursor = newest
            return [], "已连接；是否生成事件取决于 Windows 审计策略"
        status = "已连接；是否生成事件取决于 Windows 审计策略"
        if newest < self.cursor:
            self.cursor = 0
            status = "安全日志记录序号已重置，可能被清空；从现存日志继续"
        batch = query(f"*[System[{FILTER} and EventRecordID > {self.cursor}]]")
        items = []
        for event in batch:
            self.cursor = max(self.cursor, event["record_id"])
            item = public_event(event)
            if item:
                items.append(item)
        # Only advance to latest if the query did not fill its page.
        if len(batch) < 200:
            self.cursor = max(self.cursor, newest)
        return items, status
