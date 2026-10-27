# 部署指南

覆盖两种场景：

- **本地部署**：本机（Windows / macOS / Linux）用 Docker Compose 一键起全套服务
- **线上部署**：腾讯云服务器 + 宝塔面板 + Docker Compose，通过子域名 + HTTPS 对外提供服务

---

## 一、本地部署（Docker Compose）

### 1. 前置条件

- 已安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（Windows / macOS）或 Docker Engine（Linux）
- 首次使用建议配置镜像加速器，否则拉镜像很慢：
  - Docker Desktop：Settings → Docker Engine → 在 JSON 中加入 `registry-mirrors` → Apply & Restart
    ```json
    {
      "registry-mirrors": ["https://mirror.ccs.tencentyun.com", "https://docker.1panel.live"]
    }
    ```

### 2. 启动

在项目根目录执行：

```bash
cp .env.example .env      # 按需修改，务必替换 JWT_SECRET_KEY
docker compose up -d --build
```

首次启动会自动完成：构建前后端镜像 → 拉起 PostgreSQL → 执行 `alembic upgrade head` → 启动服务。

### 3. 访问地址

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:8080 |
| 后端接口文档 | http://localhost:8000/docs |

### 4. 常用命令

```bash
docker compose ps                 # 查看状态
docker compose logs -f backend    # 看后端日志
docker compose down               # 停止并移除容器
docker compose down -v            # 连数据库数据一起清除（慎用）
```

> 本地开发更推荐直接跑源码（热更新），见 [README](../README.md) 的「方式二：本地开发」。

---

## 二、线上部署（腾讯云 + 宝塔）

目标架构：

```
浏览器 ──HTTPS(443)──> 宝塔 Nginx ──127.0.0.1:8082──> frontend 容器（nginx 静态站）
                            │                              └──127.0.0.1──> /api/* 转发到 backend 容器:8000
                            └── 域名 interview.yuququan.online
```

容器端口**只绑定 127.0.0.1**，不对外暴露，外网只能通过宝塔 Nginx 的 443 进入。

### 第 1 步：准备域名解析

在域名服务商（DNSPod / 腾讯云）添加一条记录：

| 主机记录 | 记录类型 | 记录值 |
| --- | --- | --- |
| `interview` | A | 服务器公网 IP |

生效验证：

```bash
nslookup interview.yuququan.online
```

### 第 2 步：申请 SSL 证书

腾讯云控制台 → SSL 证书 → 申请免费证书 → 域名填 `interview.yuququan.online` → DNS 验证 → 签发后下载 **Nginx 格式**证书。

### 第 3 步：服务器安装 Docker

```bash
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
systemctl enable --now docker
docker -v && docker compose version
```

配置腾讯云内网镜像加速：

```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
EOF
systemctl restart docker
docker info | grep -A2 "Registry Mirrors"
```

### 第 4 步：上传代码

1. 本地打包（排除依赖与本地数据）：

   ```powershell
   powershell -ExecutionPolicy Bypass -File pack-deploy.ps1
   ```

   生成 `AI模拟面试平台-deploy.zip`（约 0.2 MB）。

2. 宝塔 → 文件 → 进入 `/www/wwwroot/ai-interview` → 上传并解压**到当前目录**。

   > 务必确认 `docker-compose.prod.yml` 直接位于 `ai-interview/` 根目录，而不是多出一层子目录。

### 第 5 步：配置生产环境变量

服务器上 `.env` 不会随代码上传（zip 已排除），首次部署需创建：

```bash
cd /www/wwwroot/ai-interview
openssl rand -hex 32     # 生成 JWT 密钥

cat > .env <<'EOF'
POSTGRES_PASSWORD=换成强密码
JWT_SECRET_KEY=粘贴上面生成的64位字符串
LLM_API_KEY=sk-你的DeepSeek密钥
EOF
```

### 第 6 步：启动容器

```bash
cd /www/wwwroot/ai-interview
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend
```

启动流程会自动执行 `alembic upgrade head`，日志出现 `Application startup complete` 即成功。

### 第 7 步：宝塔建站 + 反向代理 + SSL

1. 宝塔 → 网站 → 添加站点：域名 `interview.yuququan.online`，根目录随意，数据库「不创建」，PHP 版本「纯静态」
2. 站点设置 → SSL → 其他证书 → 粘贴腾讯云签发的证书与密钥 → 开启**强制 HTTPS**
3. 站点设置 → 配置文件，替换为：

```nginx
server {
    listen 80;
    server_name interview.yuququan.online;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name interview.yuququan.online;

    ssl_certificate     /www/server/panel/vhost/cert/interview.yuququan.online/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/interview.yuququan.online/privkey.pem;

    client_max_body_size 20m;   # 简历上传需要

    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

保存后重载 Nginx。

### 第 8 步：验证

```bash
docker compose -f docker-compose.prod.yml ps       # 三个容器均为 Up
curl -I http://127.0.0.1:8082                      # 200
curl http://127.0.0.1:8000/docs -o /dev/null -w "%{http_code}\n"   # 200
```

浏览器打开 `https://interview.yuququan.online`，注册账号验证登录链路。

---

## 三、更新部署

```bash
cd /www/wwwroot/ai-interview

# 1. 备份数据库（涉及迁移时必做）
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U ai_interview ai_interview > /root/ai_backup_$(date +%Y%m%d_%H%M).sql

# 2. 上传并解压新代码包（覆盖）

# 3. 重建容器（会自动执行数据库迁移）
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend
```

回滚：

```bash
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1   # 回退一版迁移
```

数据恢复：

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U ai_interview ai_interview < /root/ai_backup_YYYYMMDD_HHMM.sql
```

---

## 四、端口与地址约定

| 位置 | 值 | 说明 |
| --- | --- | --- |
| 容器 frontend 映射 | `127.0.0.1:8082:80` | 只监听本机，外网无法直连，无需放行防火墙 |
| 容器 backend 映射 | `127.0.0.1:8000:8000` | 同上 |
| 数据库 | 不映射端口 | 仅容器网络内可达 |
| 宝塔 Nginx `proxy_pass` | `http://127.0.0.1:8082` | 与 compose 端口保持一致 |
| Nginx `server_name` | `interview.yuququan.online` | 对外用域名 |
| `CORS_ORIGINS` | `https://interview.yuququan.online` | 与访问域名一致 |
| `DATABASE_URL` 主机 | `db` | 容器网络内的服务名 |

> 服务器 8080 端口若已被其他服务占用（如 Java 服务），改用未被占用的端口，**同时同步修改 compose 与 Nginx 的 `proxy_pass`**。

---

## 五、常见问题

### 1. 访问返回 502 Bad Gateway

原因与排查：

```bash
docker compose -f docker-compose.prod.yml ps                 # frontend 是否 Up
docker compose -f docker-compose.prod.yml logs --tail 30 frontend
curl -I http://127.0.0.1:8082                                # 容器内是否可达
grep -rn "proxy_pass" /www/server/panel/vhost/nginx/ | grep -i interview   # 端口是否对得上
```

常见结论：Nginx `proxy_pass` 端口与 compose 映射端口不一致。

### 2. 前端容器反复重启，日志含 `host not found in upstream "backend:8000"`

容器内 nginx 启动时解析不到 `backend`。`frontend/nginx.conf` 已使用 Docker 内置 DNS 动态解析：

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
set $backend_upstream backend:8000;
proxy_pass http://$backend_upstream;
```

若被覆盖成 `proxy_pass http://backend:8000;`，容器会崩溃重启。

### 3. 容器启动时报 `address already in use`

宿主机端口被占用，查看占用者并改用其他端口：

```bash
ss -tlnp | grep 8082
sed -i 's/127.0.0.1:8082:80/127.0.0.1:8083:80/' docker-compose.prod.yml
```

### 4. 构建很慢（pip / npm 阶段卡几分钟）

两个 Dockerfile 已内置腾讯云镜像源：

- `backend/Dockerfile`：`PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple`
- `frontend/Dockerfile`：`npm config set registry https://mirrors.cloud.tencent.com/npm/`

同时给 Docker 配置 `registry-mirrors`（见第 3 步），可加速基础镜像拉取。

### 5. 前端请求后端 404 / 跨域

- 生产环境不要设置 `VITE_API_BASE_URL`，构建产物会回退为相对路径 `/api/v1`，由容器内 nginx 转发到 backend
- `CORS_ORIGINS` 必须包含实际访问域名（含 `https://` 前缀）

---

## 六、附：pack-deploy.ps1

项目根目录的打包脚本，生成可直接上传到服务器的 zip：

```powershell
powershell -ExecutionPolicy Bypass -File pack-deploy.ps1
```

排除项：`node_modules`、`.venv`、`dist`、`var`、`__pycache__`、`.git`、`openspec`、`*.db`、`*.log`、`*.png`、`.ps1`。

输出到：`AI模拟面试平台-deploy.zip`（项目根目录同级）。
