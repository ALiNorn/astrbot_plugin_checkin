from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO
from mcstatus import JavaServer

import sys
sys.stdout.reconfigure(encoding='utf-8')

import base64

def draw_mc(host, port, bg_path, output_path, font_path):

    # ===== 参数区 =====
    bg_path = bg_path
    output_path = output_path

    try:
        server = JavaServer(host, port)
        status = server.status()   # Server List Ping（1.7+均支持）
        # f"MOTD　  : {status.description}",
        text_lines=[f"版本号    : {status.version.name}",
                    f"延迟        : {status.latency:.1f} ms",
                    f"在线人数 : {status.players.online} / {status.players.max}"]

        # 获取玩家列表
        player_list = []
        if status.players.sample:
            for p in status.players.sample:
                player_list.append(p.name)
                onlineplayer = "在线玩家"
        else:
            onlineplayer = "不在线玩家"
            player_list = ["Blulue","basementbat922","XianiumB","LYXSTT","MEOWKITTY"]  # 服务器没返回玩家列表
    except Exception as e:
        text_lines = [f"服务器离线或无法连接：{e}"]
        player_list = []

    # ===== 1. 下载服务器图标 =====
    avatar = Image.open(BytesIO(base64.b64decode(status.icon.removeprefix("data:image/png;base64,")))).convert("RGBA")

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

    canvas.paste(final_avatar, (55, 55), final_avatar)

    # ===== 7. 写字 =====
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(font_path, 30)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 48)
        except:
            font = ImageFont.load_default()

    text_x = 90
    text_y = 450
    line_spacing = 80

    for i, line in enumerate(text_lines):
        draw.text(
            (text_x, text_y + i * line_spacing),
            line,
            fill=(255, 255, 255, 255),
            font=font
        )

    # ===== 8. 右侧绘制玩家头像和名称 =====
    if player_list:
        # 玩家列表区域参数
        player_list_x = 450        # 玩家列表起始X（右侧区域）
        player_list_y = 130         # 玩家列表起始Y
        player_avatar_size = 70    # 小头像尺寸
        player_row_height = 80     # 每行高度
        player_name_x_offset = 80  # 头像到名称的水平间距
        player_name_font_size = 22 # 玩家名字号

        # 尝试加载字体
        try:
            player_font = ImageFont.truetype(font_path, player_name_font_size)
        except:
            try:
                player_font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", player_name_font_size)
            except:
                player_font = ImageFont.load_default()

        # 绘制标题

        draw.text(
            (player_list_x, player_list_y - 60),
            f"{onlineplayer} ({len(player_list)})",
            fill=(255, 255, 255, 255),
            font=font
        )

        for idx, player_name in enumerate(player_list):
            row_y = player_list_y + idx * player_row_height

            # 下载玩家头像
            try:
                avatar_url = f"https://littleskin.cn/avatar/player/{player_name}?size={player_avatar_size}"
                resp = requests.get(avatar_url, timeout=5)
                if resp.status_code == 200:
                    player_avatar_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                    player_avatar_img = player_avatar_img.resize(
                        (player_avatar_size, player_avatar_size), Image.LANCZOS
                    )
                else:
                    # 请求失败，用默认色块替代
                    player_avatar_img = Image.new("RGBA", (player_avatar_size, player_avatar_size), (93, 200, 243, 128))
            except Exception:
                player_avatar_img = Image.new("RGBA", (player_avatar_size, player_avatar_size), (128, 128, 128, 255))

            # 绘制圆形头像
            circle_mask = Image.new("L", (player_avatar_size, player_avatar_size), 0)
            ImageDraw.Draw(circle_mask).ellipse(
                (0, 0, player_avatar_size, player_avatar_size), fill=255
            )
            circle_avatar = Image.new("RGBA", (player_avatar_size, player_avatar_size), (0, 0, 0, 0))
            circle_avatar.paste(player_avatar_img, (0, 0), circle_mask)

            canvas.paste(circle_avatar, (player_list_x, row_y), circle_avatar)

            # 绘制玩家名（垂直居中对齐头像）
            name_y = row_y + (player_avatar_size - player_name_font_size) // 2 - 2
            draw.text(
                (player_list_x + player_name_x_offset, name_y),
                player_name,
                fill=(255, 255, 255, 255),
                font=player_font
            )

    # ===== 9. 整体圆角 =====
    corner_radius = 30
    rounded_canvas = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    round_mask = Image.new("L", (1280, 720), 0)
    ImageDraw.Draw(round_mask).rounded_rectangle(
        (0, 0, 1280, 720),
        radius=corner_radius,
        fill=255
    )

    rounded_canvas.paste(canvas, (0, 0), round_mask)

    # ===== 10. 保存 =====
    rounded_canvas.save(output_path, quality=95)
    # rounded_canvas.show()
    
if __name__ == "__main__":
    bg_path = "bg.jpg"  # 替换为实际的背景图片路径
    output_path = "mc.png"  # 输出文件路径

    host = "play.simpfun.cn"   # 或 "127.0.0.1"
    port = 19405              # Java版默认25565

    #host = "82.156.129.216"
    #port = 25565

    draw_mc(host, port, bg_path, output_path)
