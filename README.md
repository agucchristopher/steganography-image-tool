# 🔐 StegoCrypt — Steganography Image Tool

A powerful, beautifully designed Python tool to **hide secret messages inside images** using **LSB (Least Significant Bit) Steganography**.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Algorithm** | LSB Steganography (3 bits/pixel via RGB channels) |
| **Encryption** | Caesar Cipher keyed on your password |
| **Formats** | PNG, BMP, TIFF (input) → PNG (output) |
| **GUI** | Dark, modern tkinter interface with image preview |
| **CLI** | Full command-line interface for scripting |
| **Capacity Meter** | Shows how much data fits in your image |

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the GUI
```bash
python app.py
```

### 3. Use the CLI
```bash
# Hide a message
python cli.py encode -i photo.png -m "My secret" -o photo_stego.png

# Reveal a message
python cli.py decode -i photo_stego.png

# With password protection
python cli.py encode -i photo.png -m "My secret" -o photo_stego.png -p mypassword
python cli.py decode -i photo_stego.png -p mypassword

# Check image capacity
python cli.py info -i photo.png
```

---

## 📂 Project Structure

```
steganography image tool/
├── app.py              ← GUI application (main entry point)
├── cli.py              ← Command-line interface
├── steganography.py    ← Core LSB engine
├── requirements.txt    ← Dependencies
└── README.md           ← This file
```

---

## 🔬 How It Works

1. **Encoding**: Each bit of your secret message is embedded into the **least significant bit** of each RGB channel of the carrier image pixels. This change is imperceptible to the human eye.

2. **Decoding**: The LSBs are extracted from each channel and reconstructed into the original message, stopping at the embedded `<<END>>` delimiter.

3. **Password**: When a password is provided, the message is obfuscated with a **Caesar Cipher** (shift = sum of ASCII values of password characters mod 256) before embedding.

---

## ⚠️ Important Notes

- Always save the output as **PNG** — JPEG compression destroys hidden data!
- The carrier image is not modified visually; differences are invisible to the naked eye.
- A 1920×1080 PNG image can hold approximately **777,600 characters** of hidden text.

---

## 📋 Requirements

- Python 3.10+
- Pillow ≥ 10.0.0
- tkinter (included with standard Python)
