"""绘制桌面书页图标，与赛博图书馆的首页配色一致。"""
from PIL import Image, ImageDraw

image = Image.new('RGBA', (256, 256))
pen = ImageDraw.Draw(image)
pen.rounded_rectangle((8, 8, 248, 248), 44, fill='#152d30')
pen.polygon([(33,67),(117,85),(125,103),(125,199),(105,183),(33,167)], fill='#a9efcf')
pen.polygon([(133,103),(143,85),(223,64),(223,164),(153,184),(133,199)], fill='#dfbd89')
image.save('outputs/release-work/library.ico', sizes=[(n,n) for n in (16,24,32,48,64,128,256)])
