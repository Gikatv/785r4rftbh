Media Bot Pro - Full Pro Version

Features:
- TikTok + YouTube MP4 download
- MP3 audio download
- Premium bold welcome message + Chenuxx/Enigma links
- MP3/MP4 caption with duration, quality, file size
- Force Join channels ON/OFF from admin panel
- Admin panel channel button name/link/check ref add/delete/enable/disable
- User daily limit: number or unlimited
- Allowed groups add/delete
- Broadcast to users/groups
- Dashboard stats: users, downloads, broadcasts, daily downloads
- Large file > MAX_TELEGRAM_MB: direct server download link

Install:
1) unzip project
2) cd media_bot_pro
3) chmod +x install_ubuntu.sh run.sh
4) ./install_ubuntu.sh
5) cp .env.example .env
6) nano .env
7) ./run.sh

.env:
BOT_TOKEN=YOUR_BOT_TOKEN
PUBLIC_BASE_URL=http://YOUR_SERVER_IP:8080
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ApiThamaCAriyo123#
MAX_TELEGRAM_MB=1900

Admin Panel:
http://YOUR_SERVER_IP:8080/login

Force Join Notes:
- Public channel: channel_ref = @channelusername
- Private channel: channel_ref = -100xxxxxxxxxx
- Bot must be added to the channel as admin/member so it can check joins.
