import json, numpy as np
ROOT="/Users/sky/PycharmProjects/DCA"
d=json.load(open(f"{ROOT}/out/report_data.json"))
o={}
# 定投轨迹：每3个月抽样以减小体积
dts=d["dca_full"]["dates"]; cost=d["dca_full"]["cost"]; val=d["dca_full"]["value"]; h3=d["dca_hs300"]["value"]
step=1
o["dca"]={"d":dts[::step],"cost":cost[::step],"port":val[::step],"hs300":h3[::step],
          "irr":d["dca_full"]["irr"],"irr_hs":d["dca_hs300"]["irr"]}
# 滚动IRR
o["roll"]={k:{"d":v["dates"],"p":v["port"],"h":v["hs300"],"stat":v["stat"]} for k,v in d["roll"].items()}
o["corr"]=d["corr"]
o["assets"]=d["assets"]
json.dump(o,open(f"{ROOT}/out/viz.json","w"),ensure_ascii=False,separators=(",",":"))
import os; print("size",os.path.getsize(f"{ROOT}/out/viz.json"))
print("dca points",len(o["dca"]["d"]))
for k in o["roll"]: print(k,len(o["roll"][k]["p"]))
