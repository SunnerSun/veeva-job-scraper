#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Veeva职位抓取简化移动应用
使用Kivy框架制作的安卓应用
"""

import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
import threading
import urllib.request
import urllib.parse
import json
import re
import gzip

kivy.require('2.1.0')

class VeevaMobileApp(App):
    def build(self):
        self.title = "Veeva职位抓取器"
        
        # 主布局
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 标题
        title_label = Label(
            text="Veeva职位抓取器",
            size_hint_y=None,
            height=60,
            font_size=24,
            bold=True,
            halign='center'
        )
        main_layout.add_widget(title_label)
        
        # 搜索按钮
        self.search_button = Button(
            text="搜索Asia Pacific Product Support职位",
            size_hint_y=None,
            height=60,
            font_size=16
        )
        self.search_button.bind(on_press=self.start_search)
        main_layout.add_widget(self.search_button)
        
        # 进度条
        self.progress = ProgressBar(
            size_hint_y=None,
            height=20,
            max=100
        )
        main_layout.add_widget(self.progress)
        
        # 滚动视图
        scroll = ScrollView()
        self.jobs_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=5
        )
        self.jobs_layout.bind(minimum_height=self.jobs_layout.setter('height'))
        scroll.add_widget(self.jobs_layout)
        main_layout.add_widget(scroll)
        
        # 状态标签
        self.status_label = Label(
            text="点击按钮开始搜索职位",
            size_hint_y=None,
            height=40,
            font_size=14,
            halign='center'
        )
        main_layout.add_widget(self.status_label)
        
        return main_layout
    
    def start_search(self, instance):
        """开始搜索职位"""
        self.search_button.disabled = True
        self.status_label.text = "正在搜索职位..."
        self.progress.value = 0
        self.jobs_layout.clear_widgets()
        
        # 在新线程中执行搜索
        threading.Thread(target=self.search_jobs, daemon=True).start()
    
    def search_jobs(self):
        """搜索职位"""
        try:
            # 构建搜索URL
            base_url = "https://careers.veeva.com/job-search-results/"
            params = {
                'search': '',
                'remote': 'false',
                'ts': 'Product Support',
                'regions': 'Asia Pacific',
                'office_locations': ''
            }
            
            url = base_url + '?' + urllib.parse.urlencode(params)
            
            # 创建请求
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36')
            
            # 发送请求
            with urllib.request.urlopen(req) as response:
                # 处理gzip压缩
                content_encoding = response.headers.get('Content-Encoding', '').lower()
                raw_content = response.read()
                
                if content_encoding == 'gzip':
                    html_content = gzip.decompress(raw_content).decode('utf-8')
                else:
                    html_content = raw_content.decode('utf-8', errors='ignore')
            
            # 提取职位数据
            jobs = self.extract_jobs_from_html(html_content)
            
            # 在主线程中更新UI
            Clock.schedule_once(lambda dt: self.update_ui(jobs), 0)
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(str(e)), 0)
    
    def extract_jobs_from_html(self, html_content):
        """从HTML中提取职位数据"""
        try:
            # 查找allJobs变量定义
            pattern = r'let allJobs = (\[.*?\]);'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if not match:
                return []
            
            # 解析JSON数据
            jobs_json = match.group(1)
            all_jobs = json.loads(jobs_json)
            
            # 过滤Asia Pacific地区的Product Support职位
            filtered_jobs = []
            for job in all_jobs:
                team = job.get('team', '').lower()
                region = job.get('region', '').lower()
                
                if team == 'product support' and region == 'asia pacific':
                    filtered_jobs.append({
                        'job_title': job.get('job_title', 'N/A'),
                        'team': job.get('team', 'N/A'),
                        'location': f"{job.get('city', 'N/A')}, {job.get('country', 'N/A')}",
                        'region': job.get('region', 'N/A'),
                        'remote': job.get('remote', 'N/A')
                    })
            
            return filtered_jobs
            
        except Exception as e:
            print(f"提取职位数据时出错: {e}")
            return []
    
    def update_ui(self, jobs):
        """更新UI"""
        self.search_button.disabled = False
        self.progress.value = 100
        
        if jobs:
            self.display_jobs(jobs)
            self.status_label.text = f"找到 {len(jobs)} 个职位"
        else:
            self.status_label.text = "未找到职位"
            self.show_popup("提示", "未找到符合条件的职位")
    
    def show_error(self, error_msg):
        """显示错误"""
        self.search_button.disabled = False
        self.progress.value = 0
        self.status_label.text = f"错误: {error_msg}"
        self.show_popup("错误", f"搜索失败: {error_msg}")
    
    def display_jobs(self, jobs):
        """显示职位信息"""
        # 按城市分组
        cities = {}
        for job in jobs:
            city = job.get('location', 'Unknown').split(',')[0].strip()
            if city not in cities:
                cities[city] = []
            cities[city].append(job)
        
        # 显示每个城市的职位
        for city, city_jobs in sorted(cities.items()):
            # 城市标题
            city_label = Label(
                text=f"🏙️ {city} ({len(city_jobs)} 个职位)",
                size_hint_y=None,
                height=50,
                font_size=18,
                bold=True,
                color=(0.2, 0.6, 1, 1)
            )
            self.jobs_layout.add_widget(city_label)
            
            # 职位列表
            for i, job in enumerate(city_jobs, 1):
                job_text = f"职位 {i}:\n"
                job_text += f"职位标题: {job.get('job_title', 'N/A')}\n"
                job_text += f"团队: {job.get('team', 'N/A')}\n"
                job_text += f"地点: {job.get('location', 'N/A')}\n"
                job_text += f"地区: {job.get('region', 'N/A')}\n"
                job_text += f"远程工作: {'是' if job.get('remote') == '1' else '否'}"
                
                job_label = Label(
                    text=job_text,
                    size_hint_y=None,
                    height=140,
                    font_size=14,
                    text_size=(None, None),
                    halign='left',
                    valign='top',
                    markup=True
                )
                job_label.bind(size=job_label.setter('text_size'))
                self.jobs_layout.add_widget(job_label)
    
    def show_popup(self, title, message):
        """显示弹窗"""
        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(Label(text=message, text_size=(300, None)))
        
        close_button = Button(text="关闭", size_hint_y=None, height=50)
        content.add_widget(close_button)
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        
        close_button.bind(on_press=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    VeevaMobileApp().run()

