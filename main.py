import requests
import json
import telebot
from telebot import types
import uuid
import os
import datetime
import re

class FolderManager:
    def __init__(self):
        self.folders = {}  # folder_id: {name: str, chats: [], user_id: int}
        self.user_folders = {}  # user_id: [folder_ids]
        self.default_folder_name = "Основные чаты"
    
    def create_default_folder(self, user_id):
        """Создает папку по умолчанию для пользователя"""
        folder_id = str(uuid.uuid4())
        self.folders[folder_id] = {
            'name': self.default_folder_name,
            'chats': [],
            'user_id': user_id,
            'created': datetime.datetime.now()
        }
        self.user_folders[user_id] = [folder_id]
        return folder_id
    
    def get_user_folders(self, user_id):
        """Получает все папки пользователя"""
        if user_id not in self.user_folders:
            self.create_default_folder(user_id)
        return [self.folders[fid] for fid in self.user_folders.get(user_id, []) if fid in self.folders]
    
    def create_folder(self, user_id, folder_name):
        """Создает новую папку"""
        folder_id = str(uuid.uuid4())
        self.folders[folder_id] = {
            'name': folder_name,
            'chats': [],
            'user_id': user_id,
            'created': datetime.datetime.now()
        }
        if user_id not in self.user_folders:
            self.user_folders[user_id] = []
        self.user_folders[user_id].append(folder_id)
        return folder_id
    
    def delete_folder(self, user_id, folder_id):
        """Удаляет папку (только если пустая)"""
        if folder_id in self.folders and self.folders[folder_id]['user_id'] == user_id:
            if not self.folders[folder_id]['chats']:
                del self.folders[folder_id]
                self.user_folders[user_id].remove(folder_id)
                return True
        return False
    
    def move_chat_to_folder(self, chat_id, folder_id):
        """Перемещает чат в папку"""
        if folder_id in self.folders:
            # Удаляем чат из всех папок
            for folder in self.folders.values():
                if chat_id in folder['chats']:
                    folder['chats'].remove(chat_id)
            
            # Добавляем в целевую папку
            if chat_id not in self.folders[folder_id]['chats']:
                self.folders[folder_id]['chats'].append(chat_id)
            return True
        return False

class ChatManager:
    def __init__(self):
        self.user_chats = {}  # user_id: current_chat_id
        self.chats = {}       # chat_id: {messages: [], title: str, created: timestamp, user_id: int}
        self.folder_manager = FolderManager()
        
    def create_new_chat(self, user_id, folder_id=None):
        """Создает новый чат для пользователя"""
        chat_id = str(uuid.uuid4())
        self.chats[chat_id] = {
            'messages': [],
            'title': f"Чат от {datetime.datetime.now().strftime('%d.%m %H:%M')}",
            'created': datetime.datetime.now(),
            'user_id': user_id,
            'folder_id': folder_id
        }
        self.user_chats[user_id] = chat_id
        
        # Добавляем чат в папку
        if folder_id:
            self.folder_manager.move_chat_to_folder(chat_id, folder_id)
        else:
            # Добавляем в папку по умолчанию
            user_folders = self.folder_manager.get_user_folders(user_id)
            if user_folders:
                default_folder_id = user_folders[0]['name']  # Первая папка - default
                self.folder_manager.move_chat_to_folder(chat_id, list(self.folder_manager.folders.keys())[0])
        
        return chat_id
    
    def get_current_chat(self, user_id):
        """Получает текущий чат пользователя"""
        if user_id not in self.user_chats:
            return self.create_new_chat(user_id)
        return self.user_chats[user_id]
    
    def get_chat_messages(self, chat_id):
        """Получает сообщения чата"""
        return self.chats.get(chat_id, {}).get('messages', [])
    
    def add_message(self, chat_id, role, content):
        """Добавляет сообщение в чат"""
        if chat_id in self.chats:
            self.chats[chat_id]['messages'].append({
                'role': role,
                'content': content,
                'timestamp': datetime.datetime.now()
            })
            
            # Обновляем название чата на основе первого сообщения
            if len(self.chats[chat_id]['messages']) == 1 and role == 'user':
                first_msg = content[:30] + "..." if len(content) > 30 else content
                self.chats[chat_id]['title'] = first_msg
    
    def clear_chat(self, chat_id):
        """Очищает сообщения в чате"""
        if chat_id in self.chats:
            self.chats[chat_id]['messages'] = []
    
    def get_user_chats(self, user_id, folder_id=None):
        """Получает чаты пользователя (все или из конкретной папки)"""
        user_chats = {}
        for chat_id, chat_data in self.chats.items():
            if chat_data['user_id'] == user_id:
                if folder_id is None or chat_data.get('folder_id') == folder_id:
                    user_chats[chat_id] = chat_data
        return user_chats
    
    def switch_chat(self, user_id, chat_id):
        """Переключает пользователя на другой чат"""
        if chat_id in self.chats and self.chats[chat_id]['user_id'] == user_id:
            self.user_chats[user_id] = chat_id
            return True
        return False

class NekoVerseBot:
    def __init__(self):
        self.api_key = "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"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/user/NekoVerseBot",
            "X-Title": "NekoVerse AI Assistant"
        }
        self.chat_manager = ChatManager()
        
        # Специальные имена и ответы
        self.special_names = {
            "niko kvaracxelia": "სამშობლოს ვიცავ",
            "niko kvaratskhelia": "სამშობლოს ვიცავ", 
            "kvara": "სამშობლოს ვიცავ",
            "tato qardava": "სამშობლოს ვიცავ",
            "tato gardava": "სამშობლოს ვიცავ",
            "თათო ღარდავა": "სამშობლოს ვიცავ",
            "ნიკო ქვარაცხელია": "სამშობლოს ვიცავ",
            "ტატო": "სამშობლოს ვიცავ",
            "ნიკო": "სამშობლოს ვიცავ"
        }
    
    def check_special_names(self, message):
        """Проверяет, содержит ли сообщение специальные имена"""
        lower_message = message.lower()
        for name, response in self.special_names.items():
            if name in lower_message:
                return response
        return None
    
    def generate_response(self, message, user_id):
        # Сначала проверяем специальные имена
        special_response = self.check_special_names(message)
        if special_response:
            return special_response
        
        system_prompt = """Ты - NekoVerse, дружелюбный и умный AI помощник. Твое имя NekoVerse. 
        Ты общаешься вежливо, помогаешь пользователям и имеешь свою индивидуальность. 
        Отвечай на том же языке, на котором пишет пользователь. Будь креативным и engaging в общении."""
        
        # Получаем текущий чат пользователя
        chat_id = self.chat_manager.get_current_chat(user_id)
        chat_messages = self.chat_manager.get_chat_messages(chat_id)
        
        # Формируем сообщения с историей
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем историю сообщений из текущего чата
        for msg in chat_messages:
            if msg['role'] != 'system':
                messages.append({"role": msg['role'], "content": msg['content']})
        
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": "openai/gpt-5-chat",
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 1000,
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                
                # Сохраняем сообщения в историю чата
                self.chat_manager.add_message(chat_id, "user", message)
                self.chat_manager.add_message(chat_id, "assistant", ai_response)
                
                return ai_response
                
            elif response.status_code == 429:
                return "⚠️ Слишком много запросов. Подождите немного..."
                
            else:
                error_msg = f"❌ Ошибка API: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg += f"\n{error_data['error'].get('message', 'Неизвестная ошибка')}"
                except:
                    error_msg += f"\n{response.text}"
                return error_msg
                
        except requests.exceptions.Timeout:
            return "⏰ Таймаут запроса. Попробуйте еще раз."
        except requests.exceptions.ConnectionError:
            return "🔌 Ошибка соединения. Проверьте интернет."
        except Exception as e:
            return f"❌ Неожиданная ошибка: {str(e)}"
    
    def clear_current_chat(self, user_id):
        """Очищает текущий чат пользователя"""
        if user_id in self.chat_manager.user_chats:
            chat_id = self.chat_manager.user_chats[user_id]
            self.chat_manager.clear_chat(chat_id)
            return "🗑️ Текущий чат очищен!"
        return "❌ Чат не найден"
    
    def create_new_chat(self, user_id, folder_id=None):
        """Создает новый чат для пользователя"""
        self.chat_manager.create_new_chat(user_id, folder_id)
        return "🆕 Новый чат создан! Можете начать новую беседу."
    
    def get_folders_list(self, user_id):
        """Получает список папок пользователя"""
        folders = self.chat_manager.folder_manager.get_user_folders(user_id)
        if not folders:
            return "📂 У вас пока нет папок"
        
        result = "📂 Ваши папки:\n\n"
        for i, folder in enumerate(folders, 1):
            chat_count = len(folder['chats'])
            result += f"{i}. {folder['name']} ({chat_count} чатов)\n"
        
        return result
    
    def get_chats_in_folder(self, user_id, folder_name):
        """Получает чаты в конкретной папке"""
        folders = self.chat_manager.folder_manager.get_user_folders(user_id)
        for folder in folders:
            if folder['name'] == folder_name:
                chats = self.chat_manager.get_user_chats(user_id, folder['name'])
                if not chats:
                    return f"📁 Папка '{folder_name}' пуста"
                
                result = f"📁 Папка: {folder_name}\n\n"
                for i, (chat_id, chat_data) in enumerate(chats.items(), 1):
                    current_indicator = " 🔹" if user_id in self.chat_manager.user_chats and self.chat_manager.user_chats[user_id] == chat_id else ""
                    result += f"{i}. {chat_data['title']} ({len(chat_data['messages'])} сообщ.){current_indicator}\n"
                
                return result
        
        return f"❌ Папка '{folder_name}' не найдена"
    
    def create_folder(self, user_id, folder_name):
        """Создает новую папку"""
        if len(folder_name) > 50:
            return "❌ Название папки слишком длинное (макс. 50 символов)"
        
        self.chat_manager.folder_manager.create_folder(user_id, folder_name)
        return f"✅ Папка '{folder_name}' создана!"

class TelegramBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.neko_bot = NekoVerseBot()
        self.user_states = {}  # user_id: {'state': '', 'data': {}}
        self.setup_handlers()
    
    def set_user_state(self, user_id, state, data=None):
        """Устанавливает состояние пользователя"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {}
        self.user_states[user_id]['state'] = state
        if data:
            self.user_states[user_id]['data'] = data
    
    def get_user_state(self, user_id):
        """Получает состояние пользователя"""
        return self.user_states.get(user_id, {}).get('state')
    
    def clear_user_state(self, user_id):
        """Очищает состояние пользователя"""
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            welcome_text = """🐱 *Добро пожаловать в NekoVerse!*

Я ваш персональный AI помощник с системой папок и чатов!

*✨ Возможности:*
• Умные и креативные ответы
• Система папок для организации чатов
• Неограниченное количество чатов
• Сохранение истории переписки

*🔧 Основные команды:*
/start - начать общение
/new - новый чат
/clear - очистить текущий чат  
/folders - управление папками
/chats - список чатов"""
            
            markup = self.create_main_keyboard()
            self.bot.send_message(message.chat.id, welcome_text, 
                                parse_mode='Markdown', reply_markup=markup)
            self.clear_user_state(message.from_user.id)
        
        @self.bot.message_handler(commands=['new'])
        def new_chat(message):
            result = self.neko_bot.create_new_chat(message.from_user.id)
            self.bot.send_message(message.chat.id, result)
            self.clear_user_state(message.from_user.id)
        
        @self.bot.message_handler(commands=['clear'])
        def clear_chat(message):
            result = self.neko_bot.clear_current_chat(message.from_user.id)
            self.bot.send_message(message.chat.id, result)
            self.clear_user_state(message.from_user.id)
        
        @self.bot.message_handler(commands=['folders'])
        def show_folders(message):
            folders_list = self.neko_bot.get_folders_list(message.from_user.id)
            markup = self.create_folders_keyboard()
            self.bot.send_message(message.chat.id, folders_list, reply_markup=markup)
            self.clear_user_state(message.from_user.id)
        
        @self.bot.message_handler(commands=['chats'])
        def show_chats(message):
            self.set_user_state(message.from_user.id, 'view_folder_chats')
            folders_list = self.neko_bot.get_folders_list(message.from_user.id)
            self.bot.send_message(message.chat.id, 
                                f"{folders_list}\n\n📋 Введите номер папки для просмотра чатов:")
        
        @self.bot.message_handler(func=lambda message: self.get_user_state(message.from_user.id) == 'view_folder_chats')
        def handle_folder_selection(message):
            try:
                folder_num = int(message.text)
                folders = self.neko_bot.chat_manager.folder_manager.get_user_folders(message.from_user.id)
                if 1 <= folder_num <= len(folders):
                    folder_name = folders[folder_num - 1]['name']
                    chats_list = self.neko_bot.get_chats_in_folder(message.from_user.id, folder_name)
                    self.bot.send_message(message.chat.id, chats_list)
                else:
                    self.bot.send_message(message.chat.id, "❌ Неверный номер папки")
            except ValueError:
                self.bot.send_message(message.chat.id, "❌ Введите номер папки")
            self.clear_user_state(message.from_user.id)
        
        @self.bot.message_handler(func=lambda message: True)
        def handle_message(message):
            user_id = message.from_user.id
            user_text = message.text
            
            # Обработка кнопок
            if user_text == '🆕 Новый чат':
                result = self.neko_bot.create_new_chat(user_id)
                self.bot.send_message(message.chat.id, result)
                self.clear_user_state(user_id)
                return
            
            elif user_text == '🧹 Очистить чат':
                result = self.neko_bot.clear_current_chat(user_id)
                self.bot.send_message(message.chat.id, result)
                self.clear_user_state(user_id)
                return
            
            elif user_text == '📂 Папки':
                folders_list = self.neko_bot.get_folders_list(user_id)
                markup = self.create_folders_keyboard()
                self.bot.send_message(message.chat.id, folders_list, reply_markup=markup)
                self.clear_user_state(user_id)
                return
            
            elif user_text == '📁 Создать папку':
                self.set_user_state(user_id, 'creating_folder')
                self.bot.send_message(message.chat.id, "📝 Введите название для новой папки:")
                return
            
            elif user_text == '📋 Мои чаты':
                self.set_user_state(user_id, 'view_folder_chats')
                folders_list = self.neko_bot.get_folders_list(user_id)
                self.bot.send_message(message.chat.id, 
                                    f"{folders_list}\n\n📋 Введите номер папки для просмотра чатов:")
                return
            
            elif user_text == '🏠 Главная':
                markup = self.create_main_keyboard()
                self.bot.send_message(message.chat.id, "Главное меню:", reply_markup=markup)
                self.clear_user_state(user_id)
                return
            
            # Обработка состояний
            user_state = self.get_user_state(user_id)
            if user_state == 'creating_folder':
                result = self.neko_bot.create_folder(user_id, user_text)
                self.bot.send_message(message.chat.id, result)
                self.clear_user_state(user_id)
                return
            
            # Обычное сообщение
            self.bot.send_chat_action(message.chat.id, 'typing')
            response = self.neko_bot.generate_response(user_text, user_id)
            self.bot.send_message(message.chat.id, response)
    
    def create_main_keyboard(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn1 = types.KeyboardButton('🆕 Новый чат')
        btn2 = types.KeyboardButton('🧹 Очистить чат')
        btn3 = types.KeyboardButton('📂 Папки')
        btn4 = types.KeyboardButton('📋 Мои чаты')
        markup.add(btn1, btn2, btn3, btn4)
        return markup
    
    def create_folders_keyboard(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn1 = types.KeyboardButton('📁 Создать папку')
        btn2 = types.KeyboardButton('📋 Мои чаты')
        btn3 = types.KeyboardButton('🏠 Главная')
        markup.add(btn1, btn2, btn3)
        return markup
    
    def run(self):
        print("🐱 Telegram бот NekoVerse запущен!")
        print("📂 Система папок активирована...")
        self.bot.infinity_polling()

if __name__ == "__main__":
    TELEGRAM_TOKEN = "8249528196:AAFTD_8oT2dz7cQhgcKlqHSZoMXNWjDWazQ"
    
    try:
        telegram_bot = TelegramBot(TELEGRAM_TOKEN)
        telegram_bot.run()
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
