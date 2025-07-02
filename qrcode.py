from qrcodegen import QrCode, QrSegment

def print_qr(qrcode: QrCode) -> None:
	border = 2
	for y in range(-border, qrcode.get_size() + border):
		for x in range(-border, qrcode.get_size() + border):
			print("\u2588 "[1 if qrcode.get_module(x,y) else 0] * 2, end="")
		print()
	print()

def show_restaurant_code(public_key) -> None:
	text = public_key
	errcorlvl = QrCode.Ecc.LOW
	
	qr = QrCode.encode_text(text, errcorlvl)
	print_qr(qr)

def main() -> None:
	show_restaurant_code()

if __name__ == '__main__':
	main()