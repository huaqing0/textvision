# Image Context Bridge

[中文](README.zh-CN.md)

**A skill that auto-detects whether a model has vision — if not, converts images to text automatically.**

---

## What this skill does

1. **Detects** whether the model has vision capability
2. If yes — passes the image through untouched
3. If no — runs OCR to extract all visible text from the image
4. Packages the result as a structured text evidence packet
5. Sends it to the model, which can now read and reason from it

The model never sees "I can't process images." It receives structured text with
extracted content, confidence scores, file metadata, and a hard rule: *do not
invent visual details that weren't found in the text.*

---

## Example

```
Input:  screenshot of a terminal error "connection refused on port 3000"
Output: evidence packet containing:
        - "connection refused on port 3000" (confidence: 1.000)
        - filename, format, dimensions
        - confirmed facts, limitations, answering instructions
Result: the text-only model can read the error and suggest a fix
```

---

## Install

```bash
bash install.sh
```

## Use

```bash
image2context screenshot.png
image2context error.png --question "Why did the build fail?"
```

---

## License

MIT
