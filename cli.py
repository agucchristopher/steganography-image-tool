# cli version of stegocrypt for people who like the terminal (like me lol)
# honestly sometimes it's just faster than opening a browser
#
# how to use it:
#   hide a message:
#     python cli.py encode -i photo.png -m "Top secret!" -o photo_stego.png
#     python cli.py encode -i photo.png -m "Top secret!" -o photo_stego.png -p mypassword
#
#   reveal a message:
#     python cli.py decode -i photo_stego.png
#     python cli.py decode -i photo_stego.png -p mypassword
#
#   check how much you can hide in an image:
#     python cli.py info -i photo.png

import argparse
import sys
from steganography import encode_message, decode_message, image_capacity


def cmd_encode(args):
    # takes the image path, message, output path and optional password from the args
    # calls the engine and prints out what happened
    print(f"\n[→] Encoding message into '{args.image}' ...")
    result = encode_message(
        image_path=args.image,
        message=args.message,
        output_path=args.output,
        password=args.password or "",
    )
    if result["success"]:
        print(f"[✓] {result['message']}")
        print(f"    Output : {args.output}")
        print(f"    Used   : {result['used']} chars  |  Capacity: {result['capacity']} chars")
    else:
        print(f"[✗] {result['message']}", file=sys.stderr)
        sys.exit(1)


def cmd_decode(args):
    # reads the stego image and prints whatever secret message is inside
    # if no message is found it'll just say so instead of crashing
    print(f"\n[→] Decoding message from '{args.image}' ...")
    result = decode_message(
        image_path=args.image,
        password=args.password or "",
    )
    if result["success"]:
        print(f"[✓] {result['message']}")
        print("\n── Secret Message ─────────────────────────────────────")
        print(result["secret"])
        print("───────────────────────────────────────────────────────\n")
    else:
        print(f"[✗] {result['message']}", file=sys.stderr)
        sys.exit(1)


def cmd_info(args):
    # just shows some stats about the image - size, dimensions, how much it can hold
    # useful to check before trying to encode a really long message
    result = image_capacity(args.image)
    if result["success"]:
        print(f"\n[i] Image info for '{args.image}':")
        print(f"    Dimensions : {result['width']} × {result['height']} px")
        print(f"    Mode       : {result['mode']}")
        print(f"    Capacity   : ≈ {result['capacity_chars']:,} characters")
    else:
        print(f"[✗] {result.get('message', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)


def main():
    # set up the argument parser with three subcommands: encode, decode, info
    # argparse handles all the --flag stuff automatically which is super handy
    parser = argparse.ArgumentParser(
        prog="stegocrypt",
        description="StegoCrypt — LSB Steganography CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # encode subcommand - needs image, message, output, and optionally a password
    enc = sub.add_parser("encode", help="Hide a message inside an image")
    enc.add_argument("-i", "--image",    required=True, help="Carrier image path")
    enc.add_argument("-m", "--message",  required=True, help="Secret message to hide")
    enc.add_argument("-o", "--output",   required=True, help="Output stego-image path (.png)")
    enc.add_argument("-p", "--password", default="",    help="Optional password")

    # decode subcommand - just needs the image and maybe a password
    dec = sub.add_parser("decode", help="Reveal a hidden message from an image")
    dec.add_argument("-i", "--image",    required=True, help="Stego-image path")
    dec.add_argument("-p", "--password", default="",    help="Optional password")

    # info subcommand - just takes an image and shows what we can do with it
    inf = sub.add_parser("info", help="Show image info and steganography capacity")
    inf.add_argument("-i", "--image", required=True, help="Image path")

    args = parser.parse_args()

    # use a dict to route to the right function instead of a big if/elif chain
    # learned this trick online and i use it everywhere now ngl
    dispatch = {"encode": cmd_encode, "decode": cmd_decode, "info": cmd_info}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
