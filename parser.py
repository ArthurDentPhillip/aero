from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time, json, os
from datetime import datetime

# Сопоставление отправляющих городов с их страницами
FROM_CITIES = {
    "Москва": "mos.php",
    "Владивосток": "vlad.php",
    "Новосибирск": "nov.php",
    "Якутск": "yak.php"
}

# Параметры веса и объема
PARAMS = [
    {"ves": "1", "obem": "0.1"},      # Очень легкий груз
    {"ves": "5", "obem": "0.15"},     # Легкий груз
    {"ves": "10", "obem": "0.2"},     # Средний легкий груз
    {"ves": "15", "obem": "0.3"},     # Средний груз
    {"ves": "20", "obem": "0.5"},     # Средне-тяжелый груз
    {"ves": "25", "obem": "0.8"},     # Тяжелый груз
    {"ves": "50", "obem": "1.0"},     # Очень тяжелый груз
    {"ves": "100", "obem": "1.5"},    # Крупный груз
    {"ves": "200", "obem": "2.0"},    # Контейнерный груз
    {"ves": "500", "obem": "3.0"},    # Крупногабаритный груз
    {"ves": "1000", "obem": "5.0"},   # Тонна
    {"ves": "1500", "obem": "8.0"}    # Очень крупный груз
]

# Файл для сохранения результатов
RESULTS_FILE = "results.json"

def load_existing_results():
    """Загрузка существующих результатов из файла"""
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_results(results):
    """Сохранение результатов в файл"""
    try:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 Результаты сохранены в {RESULTS_FILE}")
    except Exception as e:
        print(f"❌ Ошибка сохранения результатов: {e}")

def parse_city_data(driver, wait, from_city, to_city, param, page, results):
    """Парсинг данных для одной пары городов"""
    try:
        print(f"🔄 {from_city} → {to_city} | {param['ves']} кг, {param['obem']} м³")

        # Проверяем наличие элемента выбора города
        select_element = wait.until(EC.presence_of_element_located((By.NAME, "kuda")))
        select = Select(select_element)
        
        # Проверяем, доступен ли город назначения
        available_options = [opt.get_attribute("value") for opt in select.options]
        if to_city not in available_options:
            print(f"⚠️  Город {to_city} отсутствует на странице {from_city}")
            return False

        # Выбираем город назначения
        select.select_by_value(to_city)

        # Вводим параметры
        ves_element = wait.until(EC.presence_of_element_located((By.NAME, "ves")))
        ves_element.clear()
        ves_element.send_keys(param["ves"])
        
        obem_element = driver.find_element(By.NAME, "obem")
        obem_element.clear()
        obem_element.send_keys(param["obem"])

        # Нажимаем кнопку
        if page == "vlad.php":
            submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.fordirect-param[type='submit']")))
        else:
            submit_button = wait.until(EC.element_to_be_clickable((By.ID, "knopka")))
        
        submit_button.click()

        # Ждём появления результатов
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td[align='center'][width='200'] b.h1")))
        
        # Получаем цену
        price_element = driver.find_element(By.CSS_SELECTOR, "td[align='center'][width='200'] b.h1")
        price = price_element.text.strip()

        # Авианакладная
        awb_elements = driver.find_elements(By.CSS_SELECTOR, "td[align='center'][width='200'] span.copy b")
        awb_price = awb_elements[-1].text.strip() if awb_elements else "—"

        # Срок доставки
        all_td = driver.find_elements(By.CSS_SELECTOR, "td[align='center'][width='200']")
        delivery_days = next((td.text.strip() for td in all_td if "дней" in td.text), "Не найдено")

        # Выводим результаты
        print(f"   💰 Цена: {price} руб.")
        print(f"   ✈️  Авианакладная: {awb_price} руб.")
        print(f"   ⏱ Срок: {delivery_days}\n")

        # Добавляем результат
        results.append({
            "timestamp": datetime.now().isoformat(),
            "from": from_city,
            "to": to_city.capitalize(),
            "weight": int(param["ves"]),
            "volume": float(param["obem"]),
            "company": "Аэрогруз",
            "tariff": "Основной тариф",
            "price": price,
            "delivery": delivery_days
        })
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге {from_city} → {to_city}: {str(e)}\n")
        return False

def main():
    # Настройки Chrome для GitHub Actions
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    options.binary_location = "/usr/bin/chromium-browser"  # Путь к Chromium в GitHub Actions
    
    # Загружаем существующие результаты
    results = load_existing_results()
    print(f"📊 Загружено {len(results)} существующих записей")
    
    driver = None
    try:
        # Используем встроенный chromedriver GitHub Actions
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        for from_city, page in FROM_CITIES.items():
            try:
                url = f"https://www.aerogruz.ru/calc/{page}"
                print(f"\n📍 Обработка города отправления: {from_city}")
                
                driver.get(url)
                wait = WebDriverWait(driver, 20)  # Увеличен таймаут
                
                # Ждем загрузки страницы
                wait.until(EC.presence_of_element_located((By.NAME, "kuda")))

                # Получаем список доступных городов назначения
                select_element = Select(driver.find_element(By.NAME, "kuda"))
                available_to_cities = [opt.get_attribute("value") for opt in select_element.options]

                # Исключаем город-отправитель
                available_to_cities = [city for city in available_to_cities if city and city != from_city.lower()]
                print(f"🏙️  Доступные города назначения: {', '.join(available_to_cities)}")

                for to_city in available_to_cities:
                    for param in PARAMS:
                        try:
                            # Переходим на страницу заново для каждой итерации
                            driver.get(url)
                            wait = WebDriverWait(driver, 20)
                            wait.until(EC.presence_of_element_located((By.NAME, "kuda")))
                            
                            success = parse_city_data(driver, wait, from_city, to_city, param, page, results)
                            
                            # Сохраняем результаты после каждой успешной операции
                            if success:
                                save_results(results)
                            
                            time.sleep(3)  # Увеличенная пауза между запросами
                            
                        except Exception as e:
                            print(f"⚠️  Пропущена комбинация {from_city} → {to_city} ({param['ves']}кг): {str(e)}")
                            continue
                            
            except Exception as e:
                print(f"❌ Ошибка при обработке города {from_city}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        
    finally:
        if driver:
            driver.quit()
            
        # Финальное сохранение
        save_results(results)
        print(f"\n✅ Парсинг завершен. Всего записей: {len(results)}")

if __name__ == "__main__":
    main()