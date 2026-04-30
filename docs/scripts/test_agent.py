import requests
import json
import sseclient

url = "http://127.0.0.1/v1/chat-messages"
headers = {
    "Authorization": "Bearer app-JbVcQZE3qMGNUAJzHumogicT",
    "Content-Type": "application/json"
}
payload = {
    "inputs": {},
    "query": "张先生: 你好，我的车最近充电老是充到80%就停了，而且底盘偶尔有咯噔咯噔的响声，这怎么回事？\n客服小慧: 张先生您好，很抱歉给您带来困扰。为了更准确地为您排查，我需要先核实一下您的车辆信息。请问您的车辆型号和购车日期是什么？\n张先生: 是2024款的极越01超长续航版，去年11月提的车，到现在大概跑了1.2万公里。\n客服小慧: 好的，谢谢。请问您的车牌号或车架号后6位是多少？我这边帮您建档。\n张先生: 车牌是粤A12345D，车架号后6位是253718。\n客服小慧: 已记录。您提到充电到80%停止，是使用家用充电桩还是公共快充桩？每次都这样吗？\n张先生: 家用慢充和外面的快充都试过，快充时基本到80%就跳枪，慢充偶尔能充到100%，但最近几次也都停在80%。\n客服小慧: 了解了。请问充电时仪表盘有故障灯或提示吗？底盘异响主要出现什么路况？\n张先生: 充电时会报一个“高压系统异常，请联系服务商”的提示。异响的话，基本低速过减速带或者颠簸路面时会有，速度起来就没了。\n客服小慧: 收到。根据您的描述，初步判断可能与电池管理系统（BMS）或充电协议有关，异响则可能是底盘螺栓扭矩不足或悬挂衬套磨损。建议您尽快进站进行专业检测。\n张先生: 那我现在能约明天下午去检查吗？我在广州天河区。\n客服小慧: 好的。为您查询一下广州天河中路的极越授权服务中心，明天下午14:00有空位，您方便吗？\n张先生: 可以，就14:00吧。需要带什么资料吗？\n客服小慧: 请携带车主本人身份证、行驶证和购车发票（或电子发票），我们会为您优先安排新能源三电系统检测与底盘检查。\n张先生: 好，谢谢！万一发现问题，维修要多久？我只有后天空闲。\n客服小慧: 常规检测约1小时，如果需要更换底盘部件或BMS软件升级，当天一般能完成。您可现场与工程师确认明细，我们会加急处理，争取不耽误您用车。\n张先生: 行，那我明天准时到。\n客服小慧: 好的，已为您预约成功。祝您生活愉快，再见！",
    "response_mode": "streaming",
    "user": "test-user-001"
}

resp = requests.post(url, headers=headers, json=payload, stream=True)
client = sseclient.SSEClient(resp)

tool_args = None
final_data = None

for event in client.events():
    print(f"[Event] type={event.event}")
    if event.data:
        try:
            event_data = json.loads(event.data)
            print(f"[Data] {json.dumps(event_data, ensure_ascii=False)}")
            
            # 从 agent_thought 事件中提取 tool_input
            if event_data.get("event") == "agent_thought" and event_data.get("tool_input"):
                tool_input_str = event_data.get("tool_input")
                try:
                    tool_args = json.loads(tool_input_str)
                    print(f"\n[Extracted Tool Args from agent_thought]")
                    break  # 提取到参数后立即结束循环
                except json.JSONDecodeError:
                    print(f"\n[Tool Input is not JSON] {tool_input_str}")
        except json.JSONDecodeError:
            print(f"[Data] {event.data}")
    
    if event.event == "message_end":
        final_data = json.loads(event.data)
        break

print("\n" + "="*50)
print("[Final Data]")
if final_data:
    print(json.dumps(final_data, ensure_ascii=False, indent=2))
else:
    print("No final data received")

print("\n" + "="*50)
print("[Tool Args Result]")
if tool_args:
    print(json.dumps(tool_args, ensure_ascii=False, indent=2))
else:
    print("未获取到工具调用，请检查 Agent 是否成功调用了工具。")