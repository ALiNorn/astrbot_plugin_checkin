from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO

def draw_qq(qq_number, text_lines, bg_path, output_path):

    # ===== 参数区 =====
    qq_number = qq_number
    text_lines = text_lines
    bg_path = bg_path
    output_path = output_path

    # ===== 1. 下载头像 =====
    avatar_url = f"https://thirdqq.qlogo.cn/qqapp/1905468093/583F175C3F7577BB0172F38DD76D9D87/640"
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
        font = ImageFont.truetype("loli.ttf", 60)
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
    rounded_canvas.show()

    # ===== 6. 保存 =====
    rounded_canvas.save(output_path, quality=95)
    
if __name__ == "__main__":
    qq_number = "2707059316"  # 替换为实际的QQ号
    text_lines = ["签到成功", "恭喜获得50残片", "累计签到3天"]
    bg_path = "bg.jpg"  # 替换为实际的背景图片路径
    output_path = f"{qq_number}.png"  # 输出文件路径

    draw_qq(qq_number, text_lines, bg_path, output_path)