import socket
import threading
import json
import os


def recursive_ls(path=".", level=0, max_level=2, result=None):
    if result is None:
        result = {}

    # Проверка, достигли ли максимального уровня
    if level > max_level:
        return result

    # Получение списка всех файлов и директорий в указанной директории
    entries = os.scandir(path)

    for entry in entries:
        full_path = os.path.join(path, entry.name)
        info = {
            'mode': oct(entry.stat().st_mode),
            'size': entry.stat().st_size,
            'mtime': entry.stat().st_mtime,
            'type': 'file' if entry.is_file() else 'directory'
        }

        result[full_path] = info

        if entry.is_dir():
            # Рекурсивный вызов для вложенных директорий
            recursive_ls(full_path, level + 1, max_level, result)

    return result


def run_server(stop_event):
    # Создание TCP-сокета
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Привязываем сокет к адресу и порту
    server_address = ('localhost', 8080)
    server_sock.bind(server_address)

    # Начинаем прослушивать подключения
    server_sock.listen(5)

    try:
        while not stop_event.is_set():
            # Ожидаем подключения от клиента
            connection, client_address = server_sock.accept()
            print(f'Подключение от {client_address}')

            while not stop_event.is_set():
                try:
                    # Получение данных от клиента
                    data = connection.recv(1024 * 1024).decode('utf-8')
                    received_data = json.loads(data)
                    action = received_data.get("action")
                    response = None

                    # Проверяем, был ли отправлен 0 для остановки
                    if action == "exit":
                        print("Получена команда выхода")
                        stop_event.set()
                        break

                    if action == "get_dir":
                        response = recursive_ls()
                    elif action == "change_dir":
                        dir_path = received_data.get("dir_path")
                        response = recursive_ls(path=dir_path)

                    response_data = json.dumps(response).encode()
                    connection.send(response_data)

                except json.JSONDecodeError as e:
                    # Обработка ошибки декодирования JSON
                    print(f"Произошла ошибка при декодировании JSON: {e}")
                except Exception as e:
                    # Обработка общих исключений
                    print(f"Произошла непредвиденная ошибка: {e}")
                    break

            # Закрываем соединение
            connection.close()

    finally:
        # Закрываем серверный сокет
        server_sock.close()
        print("Сервер завершил работу")


def run_client(stop_event):
    # Создание TCP-сокета
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Соединяемся с сервером
    server_address = ('localhost', 8080)
    client_sock.connect(server_address)

    try:
        while not stop_event.is_set():
            # Получаем ввод от пользователя
            user_input = input(
                "Команды:\n" +
                "get_dir - Получить информацию о директориях в JSON\n" +
                "change_dir <путь> - Получить информацию о директориях в JSON\n" +
                "exit - Выход\n")
            user_input = user_input.lower()

            # Клиент
            if user_input == 'exit':
                json_data = {"action": "exit"}
                serialized_data = json.dumps(json_data)
                client_sock.send(serialized_data.encode())
                stop_event.set()
                break
            elif user_input == 'get_dir':
                json_data = {
                    "action": "get_dir"
                }

                # Сериализация данных в JSON
                serialized_data = json.dumps(json_data)

                # Отправка данных на сервер
                try:
                    client_sock.send(serialized_data.encode())

                    # Получение подтверждения от сервера
                    response = client_sock.recv(1024 * 1024).decode()
                    response_data = json.loads(response)
                    print(f'Ответ от сервера: {response_data}')
                except ConnectionAbortedError as e:
                    # Обработка исключения, когда соединение было закрыто
                    print(f"Соединение было прервано: {e}")
                    break
                except Exception as e:
                    # Обработка общего исключения
                    print(f"Произошла непредвиденная ошибка: {e}")
                    continue
            elif " " in user_input and user_input.split(" ")[0] == "change_dir" and len(user_input.split(" ")) == 2:
                json_data = {
                    "action": "change_dir",
                    "dir_path": user_input.split(" ")[1]
                }
                serialized_data = json.dumps(json_data)

                # Отправка данных на сервер
                try:
                    client_sock.send(serialized_data.encode())

                    # Получение подтверждения от сервера
                    response = client_sock.recv(1024 * 1024).decode()
                    response_data = json.loads(response)
                    print(f'Ответ от сервера: {response_data}')
                except ConnectionAbortedError as e:
                    # Обработка исключения, когда соединение было закрыто
                    print(f"Соединение было прервано: {e}")
                    break
                except Exception as e:
                    # Обработка общего исключения
                    print(f"Произошла непредвиденная ошибка: {e}")
                    continue
            else:
                print("Неверный ввод. Попробуйте снова.")

    finally:
        # Закрываем клиентский сокет
        client_sock.close()
        print("Клиент завершил работу")


if __name__ == "__main__":
    stop_event = threading.Event()

    server_thread = threading.Thread(target=lambda: run_server(stop_event))
    server_thread.start()

    run_client(stop_event)

    server_thread.join()
