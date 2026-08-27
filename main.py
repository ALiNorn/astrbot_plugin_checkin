from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from datetime import datetime
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
import json
import random
import astrbot.api.message_components as Comp
import re


from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO

from .mczt import draw_mc

import aiohttp

@register("打卡", "查询", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        
        self.path = Path(get_astrbot_data_path()) / "plugins" / self.name
        self.data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name
        self.data_path.mkdir(parents=True, exist_ok=True)

        self.json_file = self.data_path / "sign_data.json"
        self.lock_file = self.json_file.with_suffix(".lock")

        self.data = self._load_json()

    # ----------------- 工具方法 -----------------

    def _load_json(self) -> dict:
        """安全加载 JSON"""
        if not self.json_file.exists():
            return {"version": 2, "groups": {}}

        try:
            with open(self.json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("version") != 2:
                    return self._migrate(data)
                return data
        except (json.JSONDecodeError, Exception):
            # 损坏自动恢复
            return {"version": 2, "groups": {}}

    def _migrate(self, old: dict) -> dict:
        """旧数据迁移（可扩展）"""
        return {
            "version": 2,
            "groups": old.get("groups", {})
        }

    def _save_json(self):
        """原子写 + 锁（防止并发损坏）"""
        lock = self.lock_file
        lock.touch()

        try:
            tmp = self.json_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            tmp.replace(self.json_file)
        finally:
            lock.unlink(missing_ok=True)

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _get_user_data(self, group_id: str, user_id: str) -> dict:
        """获取或初始化用户数据"""
        groups = self.data.setdefault("groups", {})
        group = groups.setdefault(group_id, {"members": {}})
        members = group.setdefault("members", {})
        return members.setdefault(user_id, {
            "frac": 0,
            "total_days": 0,
            "last_sign_date": "",
            "lottery_count": 0,
            "last_lottery_date": "",
            "gamble_count": 0,
            "last_gamble_date": ""
        })
    
    def _get_ats(self, event: AstrMessageEvent) -> str:
        """获取消息中的所有 At 用户"""
        ats = ""
        for comp in event.get_messages():
            if isinstance(comp, Comp.At):
                ats += f"{comp.qq} "
        return ats
    
    def _get_num(self, event: AstrMessageEvent) ->str:
        """获取消息中的数字"""
        s = event.message_str
        match = re.search(r'([+-]?\d+)', s)
        if match:
            num = int(match.group(1))
        return num
    
    def _draw_qq(self,qq_id, text_lines, bg_path, output_path):

        # ===== 参数区 =====
        qq_id = qq_id
        text_lines = text_lines
        bg_path = bg_path
        output_path = output_path

        # ===== 1. 下载头像 =====
        avatar_url = f"https://thirdqq.qlogo.cn/qqapp/1905468093/{qq_id}/640"
        resp = requests.get(avatar_url)
        avatar = Image.open(BytesIO(resp.content)).convert("RGBA")

        # ===== 2. 背景 =====
        bg = Image.open(bg_path).convert("RGBA").resize((1280, 720), Image.LANCZOS)
        canvas = bg.copy()

        # ===== 3. 圆角参数 =====
        avatar_size = (360, 360)
        border_size = (370, 370)   # 比头像大一圈
        radius = 44                # 圆角
        border_width = 5           # 白边粗细

        # ===== 4. 圆角白边 =====
        border = Image.new("RGBA", border_size, (255, 255, 255, 255))
        border_mask = Image.new("L", border_size, 0)
        ImageDraw.Draw(border_mask).rounded_rectangle(
            (0, 0, border_size[0], border_size[1]),
            radius=radius,
            fill=255
        )

        # ===== 5. 圆角头像 =====
        avatar = avatar.resize(avatar_size, Image.LANCZOS)
        avatar_mask = Image.new("L", avatar_size, 0)
        ImageDraw.Draw(avatar_mask).rounded_rectangle(
            (0, 0, avatar_size[0], avatar_size[1]),
            radius=radius - border_width,
            fill=255
        )

        rounded_avatar = Image.new("RGBA", avatar_size)
        rounded_avatar.paste(avatar, (0, 0), avatar_mask)
    
        # ===== 6. 组合：白边 + 头像 =====
        final_avatar = Image.new("RGBA", border_size)
        final_avatar.paste(border, (0, 0), border_mask)
        final_avatar.paste(rounded_avatar, (5, 5), rounded_avatar)

        canvas.paste(final_avatar, (55, 175), final_avatar)

        # ===== 7. 写字 =====
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype(str(self.path / f"loli.ttf"), 60)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 48)
            except:
                font = ImageFont.load_default()

        text_x = 520
        text_y = 220
        line_spacing = 80

        for i, line in enumerate(text_lines):
            draw.text(
                (text_x, text_y + i * line_spacing),
                line,
                fill=(255, 255, 255, 255),
                font=font
            )

        # ===== 8. 保存 =====
        corner_radius = 30
        rounded_canvas = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        round_mask = Image.new("L", (1280, 720), 0)
        ImageDraw.Draw(round_mask).rounded_rectangle(
            (0, 0, 1280, 720),
            radius=corner_radius,
            fill=255
        )

        rounded_canvas.paste(canvas, (0, 0), round_mask)

        # ===== 6. 保存 =====
        rounded_canvas.save(output_path, quality=95)

    # ----------------- 命令 -----------------

    @filter.command("打卡", alias={"签到", "sign"})
    async def sign(self, event: AstrMessageEvent):
        """这是一个签到指令"""
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        nickname = event.get_sender_name() or "未知"
        today = self._today()
        if group_id == "":
            group_id = "private"  # 私聊使用特殊 group_id

        user = self._get_user_data(group_id, user_id)

        sign_path = self.data_path / f"{user_id}.png"

        # 已签到判断
        if user["last_sign_date"] == today:
            yield event.plain_result(f"# 你今天已经签到过了")
            yield event.image_result(str(sign_path))
            return
    
        # 签到逻辑
        reward = random.randint(1, 100)
        user["frac"] += reward
        user["total_days"] += 1
        user["last_sign_date"] = today

        self._save_json()

        # 图片
        img_url = (
            f"http://api.tangdouz.com/wz/qd.php"
            f"?qq={user_id}"
            f"&bt=签到成功"
            f"&nr=获得{reward}残片↔签到{user['total_days']}天"
        )

        text_lines = [f"签到成功", f"恭喜获得{reward}残片", f"累计签到{user['total_days']}天"]
        
        bg = self.path / f"bg.jpg"
        self._draw_qq(str(user_id), text_lines, str(bg), str(sign_path))

        chain = [
            Comp.At(qq=event.get_sender_id()), # At 消息发送者
            Comp.Plain(f"\n# 打卡成功！\n获得{reward}残片\n累计签到{user['total_days']}天"),
            # Comp.Image.fromURL(img_url), # 从 URL 发送图片
            Comp.Image(str(sign_path)) # 从文件发送图片
        ]
        yield event.chain_result(chain)

    @filter.command("查询", alias={"签到信息","打卡信息"})
    async def sign_info(self, event: AstrMessageEvent):
        """这是一个查询信息指令"""
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        nickname = event.get_sender_name() or "未知"
        if group_id == "":
            group_id = "private"  # 私聊使用特殊 group_id

        user = self._get_user_data(group_id, user_id)

        chain = [
            Comp.At(qq=event.get_sender_id()), # At 消息发送者
            Comp.Plain(f"\n# 残片：{user['frac']}\n## 累计签到{user['total_days']}天"),
        ]
        yield event.chain_result(chain)

    @filter.command("抽奖", alias={"lottery"})
    async def lottery(self, event: AstrMessageEvent):
        """这是一个抽奖指令，花费 50 残片，随机获得 1~150 残片，每天上限15次"""
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        nickname = event.get_sender_name() or "未知"
        today = self._today()
        if group_id == "":
            group_id = "private"  # 私聊使用特殊 group_id

        user = self._get_user_data(group_id, user_id)

        if user["last_lottery_date"] != today:  # 上一次抽奖时间不是今天
            user["lottery_count"] = 0           # 重置抽奖次数
            user["last_lottery_date"] = today   # 更新抽奖日期

        if user["lottery_count"] >= 15:
            chain = [
                Comp.At(qq=event.get_sender_id()), # At 消息发送者
                Comp.Plain(f"\n# 次数太多啦！明天再来吧~"),
            ]
            yield event.chain_result(chain)
            return

        # 抽奖逻辑
        if user["frac"] < 10:
            chain = [
                Comp.At(qq=event.get_sender_id()), # At 消息发送者
                Comp.Plain(f"\n# 你残片不够哦~\n## 抽nm奖")
            ]
            yield event.chain_result(chain)
            return

        user["frac"] -= 10
        user["lottery_count"] += 1
        reward = random.randint(1, 20)  # 奖励随机数
        user["frac"] += reward
        
        self._save_json()

        if reward >10:
            reward_msg = f"## 抽奖成功\n恭喜你赚了{reward-10}残片！\n"
        elif reward < 10:
            reward_msg = f"# 哈哈哈哈\n# 亏了{10-reward}残片~\n"
        else:
            reward_msg = f"哟~不赚不亏嘛！\n"

        chain = [
            Comp.At(qq=event.get_sender_id()), # At 消息发送者
            Comp.Plain(reward_msg),
            Comp.Plain(f"## 你还有残片：{user['frac']}")
        ]
        yield event.chain_result(chain)

    @filter.command("赌博", alias={"gamble","十连"})
    async def gamble(self, event: AstrMessageEvent):
        """这是一个赌博指令，花费随机残片，获得随机残片，每天上限1次"""
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        nickname = event.get_sender_name() or "未知"
        today = self._today()
        if group_id == "":
            group_id = "private"  # 私聊使用特殊 group_id

        user = self._get_user_data(group_id, user_id)

        if user["last_gamble_date"] != today:  # 上一次赌博时间不是今天
            user["gamble_count"] = 0           # 重置赌博次数
            user["last_gamble_date"] = today   # 更新赌博日期

        if user["gamble_count"] != 0:
            chain = [
                Comp.At(qq=event.get_sender_id()), # At 消息发送者
                Comp.Plain(f"\n#今天已经赌过了！明天再来吧~"),
            ]
            yield event.chain_result(chain)
            return

        # 抽奖逻辑
        if user["frac"] < 50:
            chain = [
                Comp.At(qq=event.get_sender_id()), # At 消息发送者
                Comp.Plain(f"\n你残片不够哦~\n赌博至少要有50残片！")
            ]
            yield event.chain_result(chain)
            return

        pay = random.randint(1, 50)      # 支付随机数
        reward = random.randint(1, 150)  # 奖励随机数
        user["frac"] -= pay
        user["frac"] += reward
        user["gamble_count"] = 1
        
        self._save_json()

        if reward > pay:
            reward_msg = f"# 可恶💢\n你竟然赚了\n"
        elif reward < pay:
            reward_msg = f"## 哈哈哈哈\n# 亏了吧~\n谁叫你赌博！\n"
        else:
            reward_msg = f"恭喜！\n不赚不亏！\n"

        chain = [
            Comp.At(qq=event.get_sender_id()), # At 消息发送者
            Comp.Plain(f"\n你花了{pay}残片\n但赌到了{reward}残片\n"),
            Comp.Plain(reward_msg),
            Comp.Plain(f"你还有残片：{user['frac']}")
        ]
        yield event.chain_result(chain)

    @filter.command("赠送")
    async def give(self, event: AstrMessageEvent):
        """这是一个赠送指令"""
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        nickname = event.get_sender_name() or "未知"
        today = self._today()
        if group_id == "":
            group_id = "private"  # 私聊使用特殊 group_id

        user = self._get_user_data(group_id, user_id)

        # 获取消息中的所有 At 用户
        ats = self._get_ats(event)
        if not ats:
            chain = [
                Comp.At(qq=event.get_sender_id()), # At 消息发送者
                Comp.Plain(f"\n#请至少 At 一位用户来赠送残片哦~"),
            ]
            yield event.chain_result(chain)
            return

        # 解析赠送数量
        amount = self._get_num(event)

        if amount <= 0:
            chain = [
                Comp.At(qq=event.get_sender_id()), # At 消息发送者
                Comp.Plain(f"\n#bug修复了哦~"),
            ]
            yield event.chain_result(chain)
            return

        if user["frac"] < amount:
            chain = [
                Comp.At(qq=event.get_sender_id()), # At 消息发送者
                Comp.Plain(f"\n#你没有足够的残片来赠送！"),
            ]
            yield event.chain_result(chain)
            return

        # 扣除赠送者的残片
        user["frac"] -= amount

        # 给每个被 At 的用户增加残片
        ats = self._get_ats(event)
        target_user_id = ats
        target_user = self._get_user_data(group_id, target_user_id)
        target_user["frac"] += amount

        self._save_json()

        chain = [
            Comp.At(qq=event.get_sender_id()), # At 消息发送者
            Comp.Plain(f"\n# 赠送成功"),
            Comp.Plain(f"\n你还有残片：{user['frac']}")
        ]
        yield event.chain_result(chain)

    @filter.command("随机gb")
    async def rand_gb(self, event: AstrMessageEvent):
        """随机发送gb语录或图片"""
        user_id = event.get_sender_id()

        if user_id == 2308352808:  # 如果是gb本人
            msg = "# 完了完了，gb来了~\n# 不过还是敢发😋\n"
        else:
            msg = "## 你不是gb\n"

        gbmsgs = [
            "# 傻鸟\n",            "# 你个傻鸟！\n",
            "# 嘶溜\n",            "# 蛇你\n",
            "# 神他妈顾博神。。。\n",            "# 我是傻逼\n",
            "# 我要看\n",            "# 日尼玛\n",
            "# 真鸡儿贱\n",            "# 操你妈\n",
            "# 我后来才知道，她只是想找个机\n",            "# 没救了\n",
            "# 小可爱\n",            "# 有意思\n我要玩你\n",
            "# 能不能死远点啊\n",            "# 你有点无敌了\n"
        ]
        
        msg_id = random.randint(1, 16)  # 假设有16条语录
        msg += gbmsgs[msg_id - 1]

        pic_id = random.randint(1, 10)  # 假设有10张图片
        pic_path = self.data_path / "gb" / f"gb{pic_id}.jpg"
        if not pic_path.exists():
            # 如果图片不存在，可以选择下载或使用默认图片
            logger.warning(f"图片 {pic_path} 不存在，使用默认图片")
            pic_path = self.data_path / "gb" / "default.jpg"  # 假设有一张默认图片
        chain = [
            Comp.At(qq=event.get_sender_id()), # At 消息发送者
            Comp.Plain(msg),
            # Comp.Image(str(pic_path)) # 从文件发送图片
        ]
        yield event.chain_result(chain)
        yield event.image_result(str(pic_path))

    @filter.command("mc")
    async def test(self, event: AstrMessageEvent):
        """测试"""
        host = "play.simpfun.cn"
        port = 19405
        bg_path = str(self.path / "bg.jpg")
        output_path = str(self.data_path / "mc" / "mc.png")
        draw_mc(host, port, bg_path, output_path, str(self.path / "loli.ttf"))
        yield event.image_result(output_path)

    @filter.command("markdown",alias={"md","渲染"})
    async def markdown(self, event: AstrMessageEvent):
        """渲染markdown消息"""
        msg = event.message_str
        msg = msg.split(" ", 1)[1] if " " in msg else ""
        chain = [
            Comp.At(qq=event.get_sender_id()), # At 消息发送者
            Comp.Plain(f"{msg}"),
        ]
        yield event.chain_result(chain)

    @filter.command("arc")
    async def arcaea(self, event: AstrMessageEvent):
        """获取 Arcaea 最新版下载链接"""
        ARC_API = "https://webapi.lowiro.com/webapi/serve/static/bin/arcaea/apk"
        async with aiohttp.ClientSession() as sess:
            async with sess.get(ARC_API, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
        # data = {"success": true, "value": {"url": "...", "version": "7.0.0c"}}
        if not data.get("success"):
            yield event.plain_result("Lowiro 接口返回失败")
            return
        url = data["value"]["url"]
        ver = data["value"].get("version", "未知")
        yield event.plain_result(f"Arcaea 最新版 {ver} 下载\n [{url}]({url})")
        