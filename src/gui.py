#!/usr/bin/env python3
"""
VTW GUI - Bilibili 视频转文字工具图形界面
基于 Tkinter 构建
"""

import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from vtw import VideoProcessor, main as vtw_main
import argparse


class VTWGUI:
    """VTW 图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("VTW - Bilibili 视频转文字工具")
        self.root.geometry("900x700")
        self.root.minsize(600, 500)

        # 视频处理器
        self.processor = VideoProcessor()

        # 创建 UI
        self.create_widgets()

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        """创建所有 UI 组件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === URL 输入区 ===
        url_frame = ttk.LabelFrame(main_frame, text="视频 URL", padding="10")
        url_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(url_frame, text="输入 B站视频或 UP 主空间 URL:").pack(anchor=tk.W)

        url_input_frame = ttk.Frame(url_frame)
        url_input_frame.pack(fill=tk.X, pady=5)

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_input_frame, textvariable=self.url_var, font=("微软雅黑", 10))
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(url_input_frame, text="粘贴", command=self.paste_url, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(url_input_frame, text="清空", command=self.clear_url, width=8).pack(side=tk.LEFT, padx=5)

        # === 输出目录区 ===
        output_frame = ttk.LabelFrame(main_frame, text="输出设置", padding="10")
        output_frame.pack(fill=tk.X, pady=(0, 10))

        # 输出路径选择
        path_frame = ttk.Frame(output_frame)
        path_frame.pack(fill=tk.X, pady=5)

        ttk.Label(path_frame, text="输出目录:").pack(side=tk.LEFT)

        self.output_path_var = tk.StringVar(value=str(config.output_dir))
        output_entry = ttk.Entry(path_frame, textvariable=self.output_path_var, font=("微软雅黑", 10), width=50)
        output_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(path_frame, text="浏览", command=self.browse_output, width=8).pack(side=tk.LEFT, padx=5)

        # === 选项区 ===
        options_frame = ttk.LabelFrame(main_frame, text="处理选项", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        # 处理数量限制
        limit_frame = ttk.Frame(options_frame)
        limit_frame.pack(fill=tk.X, pady=5)

        ttk.Label(limit_frame, text="处理数量限制 (UP 主模式):").pack(side=tk.LEFT)

        self.limit_var = tk.StringVar(value="不限制")
        limit_spinbox = ttk.Spinbox(
            limit_frame,
            from_=0,
            to=100,
            textvariable=self.limit_var,
            width=15
        )
        limit_spinbox.pack(side=tk.LEFT, padx=5)

        # 强制 ASR 选项
        asr_frame = ttk.Frame(options_frame)
        asr_frame.pack(fill=tk.X, pady=5)

        self.asr_var = tk.BooleanVar(value=False)
        asr_check = ttk.Checkbutton(
            asr_frame,
            text="强制使用语音识别（不下载字幕）",
            variable=self.asr_var
        )
        asr_check.pack(side=tk.LEFT)

        # === 配置区 ===
        config_frame = ttk.LabelFrame(main_frame, text="快速配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # 配置按钮
        config_btn_frame = ttk.Frame(config_frame)
        config_btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            config_btn_frame,
            text="打开配置文件",
            command=self.open_config,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        # === 预计时间区 ===
        time_frame = ttk.LabelFrame(main_frame, text="预计时间", padding="10")
        time_frame.pack(fill=tk.X, pady=(0, 10))

        time_info_frame = ttk.Frame(time_frame)
        time_info_frame.pack(fill=tk.X, pady=5)

        self.estimated_time_var = tk.StringVar(value="待计算")
        time_label = ttk.Label(time_info_frame, text="预计耗时: ")
        time_label.pack(side=tk.LEFT)

        time_value_label = ttk.Label(
            time_info_frame,
            textvariable=self.estimated_time_var,
            font=("微软雅黑", 12, "bold"),
            foreground="#2c3e50"
        )
        time_value_label.pack(side=tk.LEFT, padx=10)

        # === 操作区 ===
        action_frame = ttk.LabelFrame(main_frame, text="操作", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))

        # 开始处理按钮
        start_btn = ttk.Button(
            action_frame,
            text="开始处理",
            command=self.start_processing,
            style="Accent.TButton",
            width=20
        )
        start_btn.pack(pady=10)

        # 停止按钮
        stop_btn = ttk.Button(
            action_frame,
            text="停止",
            command=self.stop_processing,
            state=tk.DISABLED,
            width=20
        )
        stop_btn.pack(pady=5)

        # === 进度区 ===
        progress_frame = ttk.LabelFrame(main_frame, text="处理进度", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 进度条
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=400
        )
        self.progress_bar.pack(pady=5)

        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(pady=5)

        # === 日志区 ===
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=80,
            height=12,
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 清除日志按钮
        ttk.Button(
            log_frame,
            text="清空日志",
            command=self.clear_log,
            width=10
        ).pack(anchor=tk.E, pady=5)

        # 保存按钮引用
        self.start_btn = start_btn
        self.stop_btn = stop_btn

        # 监听 URL 变化以计算预估时间
        self.url_var.trace('w', self._on_url_changed)

    def browse_output(self):
        """浏览选择输出目录"""
        selected_dir = filedialog.askdirectory(
            title="选择输出目录",
            initialdir=self.output_path_var.get()
        )
        if selected_dir:
            self.output_path_var.set(selected_dir)
            self.log(f"输出目录已更改为: {selected_dir}")

    def _on_url_changed(self, *args):
        """URL 变化时计算预估时间"""
        url = self.url_var.get().strip()
        if url:
            # 简单估算（基于经验值）
            # 单个视频：无字幕约 15-20 分钟，有字幕 < 1 分钟
            # UP 主：每个视频 1-2 分钟

            time_str = self._estimate_time(url)
            self.estimated_time_var.set(time_str)

    def _estimate_time(self, url):
        """估算处理时间"""
        # 检查是否是 UP 主
        if '/video/' not in url and 'BV' not in url:
            # UP 主模式 - 假设 5 个视频
            return "~10-20 分钟"
        else:
            # 单个视频 - 检查是否有字幕（简化判断）
            # 实际应该检查字幕是否存在，这里简化处理
            return "8-15 分钟（有字幕）/ 15-20 分钟（语音识别）"

    def paste_url(self):
        """粘贴剪贴板内容到 URL 输入框"""
        try:
            self.root.clipboard_get()
            self.url_var.set(self.root.clipboard_get())
            self.log("已从剪贴板粘贴 URL")
        except:
            self.log("剪贴板为空或无法访问")

    def clear_url(self):
        """清空 URL 输入框"""
        self.url_var.set("")
        self.estimated_time_var.set("待计算")
        self.log("URL 已清空")

    def open_config(self):
        """打开配置文件"""
        config_path = Path.cwd() / "config.json"
        try:
            import os
            os.startfile(config_path)
            self.log(f"已打开配置文件: {config_path}")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开配置文件:\n{e}")

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log("日志已清空")

    def log(self, message):
        """添加日志信息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_progress(self, value, status):
        """更新进度"""
        self.progress_var.set(value)
        self.status_var.set(status)
        self.root.update_idletasks()

    def start_processing(self):
        """开始处理"""
        url = self.url_var.get().strip()
        output_dir = self.output_path_var.get().strip()

        if not url:
            messagebox.showwarning("警告", "请输入视频或 UP 主空间 URL")
            return

        # 验证输出目录
        if not output_dir:
            messagebox.showwarning("警告", "请设置输出目录")
            return

        # 更新输出目录配置
        config.set_output_dir(output_dir)

        # 禁用开始按钮，启用停止按钮
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # 在新线程中运行处理
        self.processing_thread = threading.Thread(target=self._process_video, args=(url,))
        self.processing_thread.daemon = True
        self.processing_thread.start()

        self.log("=" * 50)
        self.log(f"开始处理: {url}")
        self.log(f"输出目录: {output_dir}")

    def _process_video(self, url):
        """在单独的线程中处理视频"""
        try:
            # 解析命令行参数
            self.update_progress(10, "正在解析 URL...")

            # 构造参数
            args = type('Args', (), {})()
            args.url = url

            # 添加选项
            limit = self.limit_var.get()
            if limit.isdigit() and int(limit) > 0:
                args.limit = int(limit)
                self.log(f"处理数量限制: {limit}")

            if self.asr_var.get():
                args.asr = True
                self.log("强制使用语音识别")

            # 创建新的解析器来捕获输出
            self.update_progress(20, "正在初始化...")

            # 使用 VideoProcessor 处理
            self.update_progress(30, "正在下载视频信息...")

            from subtitle import SubtitleDownloader
            downloader = SubtitleDownloader()

            # 判断是 UP 主还是单个视频
            if '/video/' in url or 'BV' in url:
                # 单个视频
                self.update_progress(40, "正在处理单个视频...")

                video_info = downloader.get_video_info(url)
                if not video_info:
                    self.log("错误: 无法获取视频信息")
                    messagebox.showerror("错误", "无法获取视频信息，请检查 URL 是否正确")
                    self._finish_processing()
                    return

                self.log(f"视频标题: {video_info.get('title', '未命名')}")
                self.update_progress(50, "正在提取文字...")

                # 处理视频（模拟主程序逻辑）
                result = self.processor.process_video(video_info, self.asr_var.get())

                if result:
                    self.update_progress(100, "处理完成！")
                    self.log("=" * 50)
                    messagebox.showinfo("完成", "视频处理完成！")
                else:
                    self.log("错误: 视频处理失败")
                    messagebox.showerror("错误", "视频处理失败，请查看日志")

            else:
                # UP 主模式
                self.update_progress(40, "正在获取 UP 主视频列表...")

                from subtitle import get_up_videos
                videos = get_up_videos(url, args.limit if hasattr(args, 'limit') else None)

                if not videos:
                    self.log("错误: 未找到视频")
                    messagebox.showerror("错误", "未找到视频，请检查 URL 是否正确")
                    self._finish_processing()
                    return

                self.log(f"找到 {len(videos)} 个视频")

                # 批量处理
                total = len(videos)
                for idx, video in enumerate(videos, 1):
                    progress = 40 + (60 * idx // total)
                    self.update_progress(progress, f"正在处理 [{idx}/{total}] {video.get('title', '')}")

                    result = self.processor.process_video(video, self.asr_var.get())
                    if not result:
                        self.log(f"警告: 视频处理失败 - {video.get('title', '')}")

                self.update_progress(100, "批量处理完成！")
                self.log("=" * 50)
                messagebox.showinfo("完成", f"批量处理完成！成功处理 {len(videos)} 个视频")

        except Exception as e:
            self.log(f"错误: {e}")
            messagebox.showerror("错误", f"处理过程中发生错误:\n{e}")
        finally:
            self._finish_processing()

    def stop_processing(self):
        """停止处理"""
        self.log("用户请求停止处理...")
        # 注意: 实际停止需要更复杂的实现
        # 这里只是标记停止状态
        messagebox.showinfo("提示", "停止功能正在开发中，当前无法真正停止运行中的任务")
        self._finish_processing()

    def _finish_processing(self):
        """处理完成"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def on_close(self):
        """窗口关闭事件"""
        if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
            if not messagebox.askyesno("确认退出", "处理任务正在进行中，确定要退出吗？"):
                return
        self.root.destroy()


def main():
    """主函数"""
    root = tk.Tk()

    # 设置样式
    style = ttk.Style()
    style.configure("Accent.TButton", font=("微软雅黑", 10))

    app = VTWGUI(root)

    # 居中窗口
    root.update_idletasks()
    root.eval('tk::PlaceWindow . center')

    root.mainloop()


if __name__ == "__main__":
    main()
