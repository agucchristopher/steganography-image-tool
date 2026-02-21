# main file
from PIL import Image


# this is what we put at the end of the message so we know when to stop reading
# kinda like a "that's all folks" but for bits
DELIMITER = "<<END>>"


def _text_to_bits(text: str) -> list[int]:
    # turns text into a list of 1s and 0s (binary)
    # every character becomes 8 bits, pretty standard stuff
    bits = []
    for byte in text.encode("utf-8"):
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_text(bits: list[int]) -> str:
    # does the opposite - takes raw bits and rebuilds the text
    # groups into 8 bits at a time and converts each one back to a character
    chars = []
    for i in range(0, len(bits), 8):
        byte_bits = bits[i : i + 8]
        if len(byte_bits) < 8:
            break  # not enough bits left, just stop
        byte = 0
        for bit in byte_bits:
            byte = (byte << 1) | bit
        chars.append(chr(byte))
    return "".join(chars)


def encode_message(image_path: str, message: str, output_path: str, password: str = "") -> dict:
    # this is where the magic happens!!
    # we open the image, shove the message into the pixels, and save it
    # the cool part is you literally can't see any difference in the image omg
    #
    # args:
    #   image_path  - the normal image we're hiding stuff in
    #   message     - the secret text we wanna hide
    #   output_path - where to save the new "secret" image (use .png!!)
    #   password    - optional, scrambles the msg before hiding it
    #
    # returns a dict with success, a message string, capacity and how much we used
    try:
        img = Image.open(image_path).convert("RGB")
        pixels = list(img.getdata())
        width, height = img.size
        capacity_bits = width * height * 3  # r, g, b = 3 bits per pixel
        capacity_chars = capacity_bits // 8

        # if password is given, scramble the message with a caesar cipher
        # IMPORTANT: we work on raw utf-8 bytes here, not unicode codepoints
        # doing it on codepoints broke emojis because shifting them changes their byte length
        # byte-level shift keeps everything the same size, way more reliable
        payload_bytes = message.encode("utf-8")
        if password:
            shift = sum(ord(c) for c in password) % 256  # use the password to pick a shift amount
            payload_bytes = bytes((b + shift) % 256 for b in payload_bytes)

        # tack on the delimiter so we know where the message ends when decoding
        full_payload_bytes = payload_bytes + DELIMITER.encode("utf-8")

        bits = []
        for byte in full_payload_bytes:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        if len(bits) > capacity_bits:
            # image too small for the message, gotta let the user know
            return {
                "success": False,
                "message": (
                    f"Message too large! Image can hold ≈{capacity_chars - len(DELIMITER)} chars "
                    f"but the message requires {len(full_payload_bytes)} chars."
                ),
                "capacity": capacity_chars,
                "used": len(full_payload_bytes),
            }

        # flatten all the pixel channel values into one big list
        # then we sneak one bit into the last bit of each value
        flat_pixels = [channel for pixel in pixels for channel in pixel]
        for idx, bit in enumerate(bits):
            flat_pixels[idx] = (flat_pixels[idx] & ~1) | bit  # flip just the last bit

        # now we gotta put the pixel list back into proper (r, g, b) tuples
        new_pixels = [
            (flat_pixels[i], flat_pixels[i + 1], flat_pixels[i + 2])
            for i in range(0, len(flat_pixels), 3)
        ]

        # build the new image and save it - always png so we don't lose the data!!
        new_img = Image.new("RGB", (width, height))
        new_img.putdata(new_pixels)
        new_img.save(output_path, format="PNG")

        return {
            "success": True,
            "message": "Message successfully hidden in image! ✓",
            "capacity": capacity_chars,
            "used": len(full_payload_bytes),
        }

    except FileNotFoundError:
        return {"success": False, "message": "Image file not found.", "capacity": 0, "used": 0}
    except Exception as exc:
        return {"success": False, "message": f"Error: {exc}", "capacity": 0, "used": 0}


def decode_message(image_path: str, password: str = "") -> dict:
    # reverse of encode - we dig the hidden message out of the pixel data
    # it's genuinely crazy that this works and the image looks totally normal
    #
    # args:
    #   image_path - the stego image (the one with the secret in it)
    #   password   - needs to match whatever was used when encoding
    #
    # returns dict with success, a message, and the secret text (or None if nothing found)
    try:
        img = Image.open(image_path).convert("RGB")
        pixels = list(img.getdata())

        # read the raw bits back out
        flat_pixels = [channel for pixel in pixels for channel in pixel]
        raw_bits = [p & 1 for p in flat_pixels]  # just the last bit of each one

        # reconstruct bytes one at a time and stop when we hit the delimiter
        delimiter_bytes = DELIMITER.encode("utf-8")
        dlm_len_bits    = len(delimiter_bytes) * 8

        buffer = []
        payload_bytes  = bytearray()
        found = False

        for bit in raw_bits:
            buffer.append(bit)
            if len(buffer) == 8:
                # got a full byte
                byte = 0
                for b in buffer:
                    byte = (byte << 1) | b
                payload_bytes.append(byte)
                buffer = []
                # check if the last len(delimiter_bytes) bytes match the delimiter
                if len(payload_bytes) >= len(delimiter_bytes):
                    if payload_bytes[-len(delimiter_bytes):] == delimiter_bytes:
                        payload_bytes = payload_bytes[:-len(delimiter_bytes)]  # chop off delimiter
                        found = True
                        break

        if not found:
            return {
                "success": False,
                "message": "No hidden message found in this image (or wrong password).",
                "secret": None,
            }

        # if a password was used, un-scramble it by reversing the byte shift
        if password:
            shift = sum(ord(c) for c in password) % 256
            payload_bytes = bytes((b - shift) % 256 for b in payload_bytes)

        # decode back to a string - if the password was wrong this'll look like garbage
        try:
            payload = payload_bytes.decode("utf-8")
        except UnicodeDecodeError:
            payload = payload_bytes.decode("latin-1")  # fallback so we don't crash

        return {"success": True, "message": "Message extracted successfully! ✓", "secret": payload}

    except FileNotFoundError:
        return {"success": False, "message": "Image file not found.", "secret": None}
    except Exception as exc:
        return {"success": False, "message": f"Error: {exc}", "secret": None}


def image_capacity(image_path: str) -> dict:
    # just tells you how many characters you can hide in a given image
    # bigger image = more pixels = more space, pretty obvious lol
    try:
        img = Image.open(image_path)
        w, h = img.size
        mode = img.mode
        channels = len(img.getbands())
        capacity_bits = w * h * min(channels, 3)  # max 3 channels (r, g, b)
        capacity_chars = capacity_bits // 8
        usable = capacity_chars - len(DELIMITER) - 10  # minus a little buffer just in case
        return {
            "success": True,
            "width": w,
            "height": h,
            "mode": mode,
            "capacity_chars": max(usable, 0),
        }
    except Exception as exc:
        return {"success": False, "message": str(exc)}
