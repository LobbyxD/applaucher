from PIL import Image

png = Image.open("A_flat_style_digital_vector_illustration_features_.png").convert("RGBA")

# Ensure fully transparent background
datas = png.getdata()
new_data = []
for item in datas:
    # Remove semi-white edge pixels
    if item[:3] == (255, 255, 255):
        new_data.append((255, 255, 255, 0))
    else:
        new_data.append(item)
png.putdata(new_data)

png.save("AppLauncher.ico", sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])
