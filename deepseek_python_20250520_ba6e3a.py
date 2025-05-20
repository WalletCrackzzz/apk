from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
import random
import time
import json
import os
import requests
from datetime import datetime

class WalletFinderApp(App):
    def build(self):
        return WalletFinderUI()

class WalletFinderUI(TabbedPanel):
    status_text = StringProperty("Status: INACTIVE")
    target_text = StringProperty("Target: DEMO")
    stats_text = StringProperty("Attempts: 0\nFound: 0")
    scanning_active = BooleanProperty(False)
    logged_in = BooleanProperty(False)
    progress_value = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.tab_width = 150
        
        # Initialize core data
        self.wallet_types = ["Bitcoin", "Ethereum", "Litecoin", "Binance Smart Chain", "Solana", "Cardano", "Polygon"]
        self.found_wallets = []
        self.scan_stats = {"attempts": 0, "found": 0}
        self.last_find_time = 0
        self.scan_interval = 0.1
        self.find_interval = 30
        self.discord_webhook = None
        self.target_coin = None
        self.demo_mode = True
        
        # Create tabs
        self.create_scan_tab()
        self.create_settings_tab()
        self.create_results_tab()
        self.create_support_tab()
        
        # Progress bar updater
        Clock.schedule_interval(self.update_progress, 0.1)
    
    def create_scan_tab(self):
        scan_tab = TabbedPanelItem(text='Scan')
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Status panel
        status_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.2))
        self.status_label = Label(text=self.status_text, font_size='18sp', halign='left')
        self.target_label = Label(text=self.target_text, font_size='16sp', halign='left')
        self.stats_label = Label(text=self.stats_text, font_size='16sp', halign='left')
        
        status_layout.add_widget(self.status_label)
        status_layout.add_widget(self.target_label)
        status_layout.add_widget(self.stats_label)
        layout.add_widget(status_layout)
        
        # Results list
        results_scroll = ScrollView(size_hint=(1, 0.6))
        self.results_list = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.results_list.bind(minimum_height=self.results_list.setter('height'))
        results_scroll.add_widget(self.results_list)
        layout.add_widget(results_scroll)
        
        # Scan controls
        controls_layout = BoxLayout(size_hint=(1, 0.2))
        self.start_btn = Button(text='Start Scan')
        self.start_btn.bind(on_press=self.start_scan)
        self.stop_btn = Button(text='Stop Scan', disabled=True)
        self.stop_btn.bind(on_press=self.stop_scan)
        
        controls_layout.add_widget(self.start_btn)
        controls_layout.add_widget(self.stop_btn)
        layout.add_widget(controls_layout)
        
        scan_tab.add_widget(layout)
        self.add_widget(scan_tab)
    
    def create_settings_tab(self):
        settings_tab = TabbedPanelItem(text='Settings')
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Login section
        login_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.4))
        login_layout.add_widget(Label(text='Account Login', size_hint=(1, 0.2)))
        
        self.username_input = TextInput(hint_text='Enter username', size_hint=(1, 0.2))
        self.password_input = TextInput(hint_text='Enter password', password=True, size_hint=(1, 0.2))
        
        btn_layout = BoxLayout(size_hint=(1, 0.2))
        login_btn = Button(text='Login')
        login_btn.bind(on_press=self.login)
        logout_btn = Button(text='Logout')
        logout_btn.bind(on_press=self.logout)
        
        btn_layout.add_widget(login_btn)
        btn_layout.add_widget(logout_btn)
        
        login_layout.add_widget(self.username_input)
        login_layout.add_widget(self.password_input)
        login_layout.add_widget(btn_layout)
        
        self.license_status = Label(text='Status: Not logged in (DEMO MODE)', size_hint=(1, 0.2))
        login_layout.add_widget(self.license_status)
        layout.add_widget(login_layout)
        
        # Webhook section
        webhook_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.3))
        webhook_layout.add_widget(Label(text='Discord Webhook Setup', size_hint=(1, 0.3)))
        
        self.webhook_input = TextInput(hint_text='Enter webhook URL', size_hint=(1, 0.3))
        if self.discord_webhook:
            self.webhook_input.text = self.discord_webhook
        
        webhook_btn = Button(text='Save Webhook', size_hint=(1, 0.3))
        webhook_btn.bind(on_press=self.save_webhook)
        
        webhook_layout.add_widget(self.webhook_input)
        webhook_layout.add_widget(webhook_btn)
        layout.add_widget(webhook_layout)
        
        settings_tab.add_widget(layout)
        self.add_widget(settings_tab)
    
    def create_results_tab(self):
        results_tab = TabbedPanelItem(text='Results')
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Toolbar
        toolbar = BoxLayout(size_hint=(1, 0.1))
        self.sort_spinner = Spinner(text='Newest First', values=['Newest First', 'Oldest First', 'By Coin', 'By Balance'])
        
        sort_btn = Button(text='Sort')
        sort_btn.bind(on_press=self.sort_results)
        export_btn = Button(text='Export')
        export_btn.bind(on_press=self.export_results)
        
        toolbar.add_widget(self.sort_spinner)
        toolbar.add_widget(sort_btn)
        toolbar.add_widget(export_btn)
        layout.add_widget(toolbar)
        
        # Results display
        scroll = ScrollView()
        self.results_text = Label(text='No results yet', size_hint_y=None, halign='left', valign='top')
        self.results_text.bind(texture_size=self.results_text.setter('size'))
        scroll.add_widget(self.results_text)
        layout.add_widget(scroll)
        
        results_tab.add_widget(layout)
        self.add_widget(results_tab)
    
    def create_support_tab(self):
        support_tab = TabbedPanelItem(text='Support')
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        layout.add_widget(Label(text='Support & Contact', font_size='20sp'))
        layout.add_widget(Label(text='Telegram Support: @Walletcrackz'))
        
        telegram_btn = Button(text='Join Telegram Group')
        telegram_btn.bind(on_press=lambda x: self.open_url("https://t.me/Walletcrackzzz"))
        layout.add_widget(telegram_btn)
        
        contact_label = Label(text='Contact: @Walletcrackz', color=(0.16, 0.51, 0.85, 1))
        layout.add_widget(contact_label)
        
        support_tab.add_widget(layout)
        self.add_widget(support_tab)
    
    def open_url(self, url):
        try:
            import webbrowser
            webbrowser.open(url)
        except:
            self.show_popup("Error", "Could not open browser")
    
    def show_popup(self, title, message):
        popup = Popup(title=title, size_hint=(0.8, 0.4))
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=message))
        btn = Button(text='OK')
        btn.bind(on_press=popup.dismiss)
        content.add_widget(btn)
        popup.content = content
        popup.open()
    
    def start_scan(self, instance):
        self.scanning_active = True
        self.status_text = "Status: ACTIVE"
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        
        # Start scanning in a separate thread (using Clock for Kivy compatibility)
        Clock.schedule_interval(self.scan_tick, self.scan_interval)
    
    def stop_scan(self, instance):
        self.scanning_active = False
        self.status_text = "Status: INACTIVE"
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        Clock.unschedule(self.scan_tick)
        self.progress_value = 0
    
    def scan_tick(self, dt):
        if not self.scanning_active:
            return
            
        self.scan_stats['attempts'] += 1
        self.stats_text = f"Attempts: {self.scan_stats['attempts']}\nFound: {self.scan_stats['found']}"
        
        # Simulate finding a wallet periodically
        if not self.logged_in and time.time() - self.last_find_time > self.find_interval:
            self.last_find_time = time.time()
            self.scan_stats['found'] += 1
            self.stats_text = f"Attempts: {self.scan_stats['attempts']}\nFound: {self.scan_stats['found']}"
            
            wallet_type = random.choice(self.wallet_types)
            seed = self.generate_seed()
            address = self.generate_address(wallet_type)
            btc, usd = self.generate_balance()
            
            wallet_data = {
                'type': wallet_type,
                'address': address,
                'valid': False,
                'btc': btc,
                'usd': usd,
                'seed': seed,
                'demo': True,
                'timestamp': time.time()
            }
            
            self.found_wallets.append(wallet_data)
            if len(self.found_wallets) > 100:
                self.found_wallets.pop(0)
            
            self.update_results_display(wallet_data)
    
    def generate_seed(self):
        bip39_words = ["abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse", 
                      # ... (include all BIP39 words from original code)
                      "zone", "zoo"]
        return ' '.join(random.choices(bip39_words, k=12))
    
    def generate_address(self, wallet_type):
        coin = wallet_type.upper()
        prefixes = {
            "BITCOIN": ["1", "3", "bc1"],
            "ETHEREUM": ["0x"],
            "LITECOIN": ["L", "M", "ltc1"],
            "BINANCE SMART CHAIN": ["0x", "bnb"],
            "SOLANA": ["So"],
            "CARDANO": ["addr"],
            "POLYGON": ["0x"]
        }
        prefix = random.choice(prefixes.get(coin, ["addr"]))
        chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        return prefix + ''.join(random.choices(chars, k=33-len(prefix)))
    
    def generate_balance(self):
        btc_amount = random.uniform(0.000002, 0.0005)
        usd_value = round(btc_amount * 50000, 5)
        return btc_amount, usd_value
    
    def update_results_display(self, wallet_data):
        if wallet_data['demo']:
            color = "#FFD700"
            status = "DEMO"
        elif wallet_data['valid']:
            color = "#00FF00"
            status = "VALID"
        else:
            color = "#FF0000"
            status = "INVALID"
        
        # Add to results list
        result_label = Label(text=f"{wallet_data['address']} - {wallet_data['type']} - {status}", 
                           color=self.hex_to_rgb(color), 
                           size_hint_y=None, height=40)
        self.results_list.add_widget(result_label, index=0)
        
        # Update results text
        self.display_results_in_text()
    
    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)) + (1,)
    
    def display_results_in_text(self):
        seen_addresses = set()
        results = []
        
        for wallet in sorted(self.found_wallets, key=lambda x: x['timestamp'], reverse=True):
            if wallet['address'] in seen_addresses:
                continue
            seen_addresses.add(wallet['address'])
            
            if wallet['demo']:
                color = "gold"
                status = "DEMO"
            elif wallet['valid']:
                color = "green"
                status = "VALID"
            else:
                color = "red"
                status = "INVALID"
                
            result_text = f"""{wallet['type']} Wallet Found!
Address: {wallet['address']}
Balance: {wallet['btc']:.8f} BTC (~${wallet['usd']:.2f})
Seed: {'[DEMO MODE - LOGIN REQUIRED]' if wallet['demo'] else wallet['seed']}
Status: {status}
Found: {datetime.fromtimestamp(wallet['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
{'='*40}
"""
            results.append(result_text)
        
        self.results_text.text = '\n'.join(results)
    
    def sort_results(self, instance):
        sort_option = self.sort_spinner.text
        
        if sort_option == "Newest First":
            self.found_wallets.sort(key=lambda x: x['timestamp'], reverse=True)
        elif sort_option == "Oldest First":
            self.found_wallets.sort(key=lambda x: x['timestamp'])
        elif sort_option == "By Coin":
            self.found_wallets.sort(key=lambda x: x['type'])
        elif sort_option == "By Balance":
            self.found_wallets.sort(key=lambda x: x['btc'], reverse=True)
            
        self.display_results_in_text()
    
    def export_results(self, instance):
        # On Android, we'll save to app storage
        try:
            from android.storage import app_storage_path
            save_path = os.path.join(app_storage_path(), "wallet_results.txt")
            with open(save_path, 'w') as f:
                f.write(self.results_text.text)
            self.show_popup("Success", f"Results saved to:\n{save_path}")
        except:
            self.show_popup("Error", "Could not save results")
    
    def update_progress(self, dt):
        self.progress_value = (self.progress_value + 1) % 100
    
    def login(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        
        if not username or not password:
            self.show_popup("Error", "Please enter both username and password")
            return
        
        # Simplified authentication for demo
        if username == "admin" and password == "password":
            self.logged_in = True
            self.demo_mode = False
            self.target_coin = "Ethereum"  # Default target
            self.license_status.text = f"Logged in - Scanning: {self.target_coin}"
            self.target_text = f"Target: {self.target_coin}"
            self.show_popup("Success", f"Logged in successfully!\nScanning for: {self.target_coin}")
            self.username_input.text = ""
            self.password_input.text = ""
        else:
            self.show_popup("Error", "Invalid username or password")
    
    def logout(self, instance):
        self.logged_in = False
        self.demo_mode = True
        self.target_coin = None
        self.license_status.text = "Status: Not logged in (DEMO MODE)"
        self.target_text = "Target: DEMO (scanning all)"
        self.show_popup("Success", "Logged out successfully")
    
    def save_webhook(self, instance):
        url = self.webhook_input.text.strip()
        self.discord_webhook = url if url else None
        self.show_popup("Success", "Webhook settings saved")

if __name__ == '__main__':
    WalletFinderApp().run()
