# PPM-архиватор

Установка зависимостей (в папку с проектом):

`pip install -r requirements.txt -t .`

где `-t <project_folder>`

Установит fenwick (дерево для хранения частот), bitarray (побитовое чтение/запись)

## Примеры использования:

```
python main.py zip test.txt test.zip
python main.py unzip test.zip test_unzip.txt

# - для stdin/stdout
python main.py zip - test.zip
python main.py unzip test.zip -

# через пайп в stdout
python main.py zip test.txt - | python main.py unzip - -
```

Баги возможны...

## Опции энкодера

Декодеру опции не нужны, он читает из заголовка архива

Все опции имеют дефолтное значение на основании лучшего бенчмарка текста из задания

Описание из кода:
```
'mode': type=str, choices=['zip', 'unzip']
'source_file': type=str
'dest_file': type=str
'-K', '--ctx_length': type=int, default=5
'-m', '--mask': type=bool, default=True
'-e', '--exclude': type=bool, default=False
'-u', '--up_algo': type=str, choices=['A', 'B', 'C', 'D'], default='D'
'-c', '--decapitalize': type=bool, default=False
```

Пример:
```
python zip test.txt test.zip --ctx_length 4 -m True --exclude False -u A -c True
```