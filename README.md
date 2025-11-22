# qbittorrent 自动删除任务脚本
因为需要搭配nastool使用,不能使用内置的torrent管理功能,所以才有这个脚本
***
使用方法: docker部署
```
docker push coolkid903/qbittorrent-automate:latest
```

环境变量配置
```
# qBittorrent 配置
QB_URL=http://localhost
QB_PORT=8080
QB_USERNAME=admin
QB_PASSWORD=adminadmin

# 清理条件配置
RATIO_LIMIT=2.0
SEEDING_TIME_LIMIT=120  # 分钟
DELETE_FILES=false

# 分类过滤
EXCLUDE_TAGS=NASTOOL
INCLUDE_TAGS=

# 调度器配置
CHECK_INTERVAL=60  # 检查间隔（分钟）
```
