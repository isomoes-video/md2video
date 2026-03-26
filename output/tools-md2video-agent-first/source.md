---
title: 'md2video：一种 Agent-First 的 Markdown 转视频方式'
date: '2026-03-26'
tags: ['md2video', 'agent-first', 'ai-workflow', 'markdown', 'video-generation', 'cui', 'mcp', 'skills']
summary: 'md2video 是一个很小但很有代表性的 agent-first 软件实验：它的主输入不是 GUI 表单，也不是 SDK 调用，而是给 AI agent 使用的 prompt 文件，最终把 markdown 源内容生成带旁白的幻灯片视频。'
locale: zh
translationKey: tools-md2video-agent-first
---

## 为什么 md2video 值得写一篇文章

大多数软件到今天为止，依然是围绕“人类操作者”来设计的。我们会做一个 GUI 让人去点，也会做一个 CLI 让人去敲，还会提供一个 SDK 让程序员把它接到别的系统里。但 md2video 的出发点不太一样：在越来越多工作流里，真正的一线操作者已经开始变成 AI agent。

## Skills + MCP + Workspace

实际问题其实很简单：怎样让被打包的知识和被打包的工具，在同一个工作空间里协同工作？md2video 给出了一个很直观的答案。仓库里有定义各阶段行为的 prompt 文件，有定义幻灯片结构和样式要求的 reveal.js skill，也有负责语音生成和视频拼接的辅助脚本。

## 从 GUI、CLI 到 CUI

对于很多 AI 工作流来说，主要界面已经不再是传统 GUI，甚至也不只是经典 CLI。越来越多时候，真正的主界面其实是聊天回路本身：用户用自然语言表达目标，agent 再决定该调用哪些 prompt、哪些文件、哪些工具。

## md2video 是怎样把 Markdown 变成视频的

整个流程很直接：先生成 reveal.js 演示文稿和 narration script，再生成逐页旁白音频，最后把 PDF 页面和对应的 MP3 合成为最终视频。

## 一个很小的项目，但指向了更大的方向

md2video 本身是一个很简洁的项目，但它背后的想法比仓库本身要大得多。它在暗示，未来的软件交付形态可能不只是 app 和 library，也会越来越多地变成 agent workspace。
