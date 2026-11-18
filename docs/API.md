# 接口

`POST /api/run`：JSON中的csv文本，省略使用样例；或multipart字段file。可选policy（urgent_first急单先、set_first成套先，默认急单先），也可用查询参数传入；无效策略422。最大5MB。

`POST /api/m1`至`POST /api/m7`：独立运行到指定模块，JSON结构同运行接口；`/api/m5`返回两种策略的compare对照。

`GET /api/history`：历史批次。`POST /api/review`接收id、revision和decision（通过或退回）。`GET /api/evidence.csv`提供单一证据导出。

结构错误422，版本变化409，文件过大413；错误返回code与message。所有页面可从左侧七个模块入口访问。

`GET /api/runs/<id>`读取指定批次；页面与证据CSV通过run_id查询参数绑定批次，模块导航保留该参数。

JSON请求体必须是对象，数组、标量、null、损坏JSON及错误上传字段返回400，且不运行默认样例。
