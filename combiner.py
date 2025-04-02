import os

def combine_py_files(root_dir, output_file, exclude_dirs=None):
    """
    Собирает содержимое всех .py файлов проекта в один текстовый файл.
    
    :param root_dir: Корневая директория проекта
    :param output_file: Путь к выходному файлу
    :param exclude_dirs: Список исключаемых директорий
    """
    if exclude_dirs is None:
        exclude_dirs = ['venv', '__pycache__', '.git', '.idea', 'env', 'manuals', 'my_trading', 'tools',
                        'dev_scripts', 'mydigest', 'session', 'test']
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(root_dir):
            # Исключаем ненужные директории
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for filename in files:
                if filename.endswith('.py') and filename != 'combiner.py':
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, root_dir)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            contents = infile.read()
                    except Exception as e:
                        print(f"⚠️ Ошибка при чтении {file_path}: {e}")
                        continue
                    
                    # Записываем в выходной файл
                    outfile.write(f"{'-' * 33}\n")
                    outfile.write(f"{rel_path}:\n")
                    outfile.write(f"{'-' * 33}\n")
                    outfile.write(contents)
                    outfile.write("\n")

if __name__ == "__main__":
    combine_py_files(
        root_dir='.',  # Укажите путь к вашему проекту
        output_file='combined_code.txt'
    )