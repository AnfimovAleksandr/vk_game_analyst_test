import time
import os
import winreg
import re

def get_steam_path():
    '''Поиск пути для Steam'''
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        return steam_path
    except:
        return None

def get_app_name(steam_path, appid):
    '''Поиск назания игры'''
    manifest_path = os.path.join(steam_path, "steamapps", f"appmanifest_{appid}.acf")
    if not os.path.exists(manifest_path):
        return f"AppID {appid}"
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'"name"\s+"([^"]+)"', content)
            if match:
                return match.group(1)
    except:
        pass
    return f"AppID {appid}"

def get_download_info(steam_path):
    '''Сбор инфы по загрузке'''

    log_path = os.path.join(steam_path, "logs", "content_log.txt")
    if not os.path.exists(log_path):
        return None, None, None
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-100:]  # Последние 100 строк вроде достаточно
        
        # Анализируем лог снизу вверх
        removed_appids = set()
        paused_appid = None
        active_appid = None
        speed = 0.0
        
        for line in reversed(lines):

            # 1. Если игра установлена, расходимся
            if 'state changed : Fully Installed' in line:
                break

            # 2. Запоминаем удалённые игры (на случай, если будем удалять другие игры одновременно с установкой)
            if 'state changed : Uninstalled' in line or 'finished uninstall' in line.lower():
                match = re.search(r'AppID (\d+)', line)
                if match:
                    removed_appids.add(match.group(1))
            
            # 2. Ищем скорость (актуальна только для активных загрузок)
            if not speed:
                rate_match = re.search(r'Current download rate:\s*([\d.]+)\s*Mbps', line)
                if rate_match:
                    speed = float(rate_match.group(1)) / 8.0  # Конвертация в МБ/с
            
            # 3. Определяем статус игры
            appid_match = re.search(r'AppID (\d+)', line)
            if not appid_match:
                continue
            
            appid = appid_match.group(1)
            if appid in removed_appids:
                continue  # Игра удалена — пропускаем
            
            # Статус "Пауза"
            if 'state changed' in line and '(Suspended)' in line and 'Uninstalled' not in line:
                paused_appid = appid
                break
            
            # Статус "Активно"
            if 'App update changed : Running Update,Downloading,Staging,' in line and 'Stopping' not in line:
                active_appid = appid
                break
        
        # Определяем результат
        current_appid = paused_appid or active_appid
        if not current_appid:
            return None, None, None
        
        game = get_app_name(steam_path, current_appid)
        # Если имя игры не получено из манифеста (файл удалён) — считаем загрузку отменённой
        if game.startswith("AppID"):
            return None, None, None
        
        status = "Пауза" if paused_appid else "Активно"
        if paused_appid:
            speed = 0.0
        
        return speed, status, game
    
    except Exception as e:
        return None, None, None

def main():
    steam_path = get_steam_path()
    if not steam_path:
        print("Не найден путь установки Steam в реестре")
        return
    
    print("Мониторинг загрузок Steam (5 минут, обновление каждую минуту)...\n")
    
    for i in range(5):
        speed, status, game = get_download_info(steam_path)
        
        if game is not None:
            print(f"[{i+1}/5] Игра: {game}")
            print(f"Скорость: {speed:.2f} МБ/с | Статус: {status}\n")
        else:
            print(f"[{i+1}/5] Активная загрузка не обнаружена\n")
        
        if i < 4:
            time.sleep(60)

if __name__ == "__main__":
    main()