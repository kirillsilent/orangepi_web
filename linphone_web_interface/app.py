import json
import subprocess
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os

app = Flask(__name__)

# Путь к файлу конфигурации
CONFIG_FILE = '/home/orangepi/linphone_web_interface/config.json'

# Функция для чтения конфигурации
def read_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Если конфигурации нет, возвращаем пустой словарь
        return {}

# Функция для записи конфигурации
def write_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Функция для пинга Google DNS (8.8.8.8)
def ping_server():
    try:
        response = os.system("ping -c 1 8.8.8.8")
        print(f"Ping response: {response}")  # Выводим результат пинга
        return response == 0  # Возвращает True, если пинг прошел успешно
    except Exception as e:
        print(f"Ошибка при пинге: {e}")
        return False
@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'ping': True}), 200


# Получение уровня громкости
def get_volumes():
    try:
        result = subprocess.run(['amixer', 'sget', 'Speaker'], capture_output=True, text=True)
        master_volume = int(result.stdout.split("[")[1].split("%")[0])

        result = subprocess.run(['amixer', 'sget', 'Mic'], capture_output=True, text=True)
        pcm_volume = int(result.stdout.split("[")[1].split("%")[0])

        return {'master': master_volume, 'pcm': pcm_volume}
    except Exception as e:
        print(f"Ошибка получения громкости: {e}")
        return {'master': 0, 'pcm': 0}

# Установка уровня громкости
def set_volume(control, volume):
    try:
        subprocess.run(['amixer', 'sset', control, f'{volume}%'], check=True)
        return True
    except Exception as e:
        print(f"Ошибка установки громкости {control}: {e}")
        return False

# Получение списка аудиоустройств
def get_audio_devices():
    try:
        output_result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        output_devices = [
            {'name': line.split(':')[1].strip()} 
            for line in output_result.stdout.splitlines() if "card" in line
        ]

        input_result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        input_devices = [
            {'name': line.split(':')[1].strip()} 
            for line in input_result.stdout.splitlines() if "card" in line
        ]

        return {'output': output_devices, 'input': input_devices}
    except Exception as e:
        print(f"Ошибка получения списка устройств: {e}")
        return {'output': [], 'input': []}

# Получение списка видеоустройств
def get_video_devices():
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True)
        devices = []
        device = None
        # Печатаем вывод для отладки
        print(result.stdout)

        for line in result.stdout.splitlines():
            if "dev/video" in line:
                device = line.strip()
            elif device:
                devices.append({'name': device})
                device = None

        print(f"Найденные видеоустройства: {devices}")  # Отладочный вывод
        return devices
    except Exception as e:
        print(f"Ошибка получения списка видеоустройств: {e}")
        return []

# Установка устройства по умолчанию
def set_default_device(device_type, device_name):
    try:
        if device_type == 'output':
            subprocess.run(['amixer', 'cset', 'numid=3', device_name], check=True)
        elif device_type == 'input':
            subprocess.run(['arecord', '-D', device_name], check=True)
        return True
    except Exception as e:
        print(f"Ошибка установки устройства {device_type}: {e}")
        return False

@app.route('/get_volume', methods=['GET'])
def get_volumes_route():
    return jsonify(get_volumes())

@app.route('/set_volume', methods=['POST'])
def set_volume_route():
    data = request.get_json()
    control = data.get('control')
    volume = data.get('volume')
    print(f"Установка громкости {control} на {volume}%")
    if set_volume(control, volume):
        return jsonify({'success': True}), 200
    return jsonify({'success': False}), 500

@app.route('/get_audio_devices', methods=['GET'])
def get_audio_devices_route():
    return jsonify(get_audio_devices())

@app.route('/set_audio_device/<device_type>/<device_name>', methods=['POST'])
def set_audio_device_route(device_type, device_name):
    if set_default_device(device_type, device_name):
        return jsonify({'success': True}), 200
    return jsonify({'success': False}), 500

@app.route('/get_video_devices', methods=['GET'])
def get_video_devices_route():
    return jsonify(get_video_devices())

@app.route('/set_video_device/<device_name>', methods=['POST'])
def set_video_device_route(device_name):
    # Логика установки видеоустройства
    try:
        subprocess.run(['v4l2-ctl', '--device', device_name, '--set-fmt-video', 'pixelformat=YUYV'], check=True)
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Ошибка установки видеоустройства: {e}")
        return jsonify({'success': False}), 500

@app.route('/get_audio_settings', methods=['GET'])
def get_audio_settings():
    config = read_config()
    volumes = get_volumes()
    devices = get_audio_devices()
    video_devices = get_video_devices()
    return jsonify({
        'master_volume': config.get('master_volume', volumes.get('master')),
        'pcm_volume': config.get('pcm_volume', volumes.get('pcm')),
        'output_device': config.get('output_device', ''),
        'input_device': config.get('input_device', ''),
        'video_device': config.get('video_device', ''),
        'available_devices': devices,
        'available_video_devices': video_devices
    })

@app.route('/set_audio_settings', methods=['POST'])
def set_audio_settings():
    try:
        data = request.get_json()
        master_volume = data.get('master_volume')
        pcm_volume = data.get('pcm_volume')
        output_device = data.get('output_device')
        input_device = data.get('input_device')
        video_device = data.get('video_device')

        if master_volume is not None:
            set_volume('Speaker', master_volume)
        if pcm_volume is not None:
            set_volume('Mic', pcm_volume)

        if output_device:
            set_default_device('output', output_device)
        if input_device:
            set_default_device('input', input_device)
        if video_device:
            subprocess.run(['v4l2-ctl', '--device', video_device, '--set-fmt-video', 'pixelformat=YUYV'], check=True)

        config = read_config()
        config.update({
            'master_volume': master_volume,
            'pcm_volume': pcm_volume,
            'output_device': output_device,
            'input_device': input_device,
            'video_device': video_device
        })
        write_config(config)

        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Ошибка сохранения настроек: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    ping_successful = ping_server()
    return render_template('index.html', ping_successful=ping_successful)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        server = request.form['server']
        username = request.form['username']
        password = request.form['password']
        operator = request.form['operator']

        config = {
            'server': server,
            'username': username,
            'password': password,
            'operator': operator
        }

        write_config(config)

        #subprocess.run(['pkill','linphonec'])
        #subprocess.run(['pkill','linphonecsh'])
       # subprocess.run(['linphonecsh', 'init', '-c', '.linphonerc', '-a', '-C'])
        subprocess.run(['linphonecsh', 'unregister'])
        subprocess.run(['linphonecsh', 'register', '--host', server, '--username', username, '--password', password])

        with open('/home/orangepi/g.sh', 'r') as file:
            lines = file.readlines()

        lines[9] = f"linphonecsh dial {operator}\n"

        with open('/home/orangepi/g.sh', 'w') as file:
            file.writelines(lines)

        return redirect('/settings')

    config = read_config()
    return render_template('settings.html', config=config)

@app.route('/get_config', methods=['GET'])
def get_config():
    config = read_config()
    return jsonify(config)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=8080)
