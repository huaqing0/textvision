# Image Context Bridge

[English](README.md)

**一个 Skill，自动检测模型有没有视觉能力——没有就自动把图片转成文字。**

---

## 这个 Skill 做什么

1. **检测**模型有没有视觉能力
2. 有——图片原封不动传过去
3. 没有——自动 OCR 提取图片里所有可见文字
4. 打包成一份结构化的文字证据
5. 发给模型，模型现在能读懂并推理了

模型永远看不到「我无法处理图片」。它收到的是一份结构化文本——包含提取的内容、
置信度、文件信息，以及一条硬约束：*不要编造文字里没有的视觉细节。*

---

## 示例

```
输入：一张终端报错截图 「connection refused on port 3000」
输出：证据包，包含：
      - 「connection refused on port 3000」（置信度 1.000）
      - 文件名、格式、尺寸
      - 确认的事实、局限性、回答指引
结果：纯文本模型能读懂报错内容，给出修复建议
```

---

## 安装

```bash
bash install.sh
```

## 使用

```bash
image2context screenshot.png
image2context error.png --question "为什么构建失败了？"
```

---

## 许可

MIT
