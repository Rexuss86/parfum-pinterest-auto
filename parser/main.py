#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер DNK Parfum — ОТЛАДОЧНАЯ ВЕРСИЯ с подробным логированием
"""

import time
import json
import re
import argparse
import random
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import hashlib

BASE_URL = "https://dnkparfum.ru"
OUTPUT_DIR = Path("data")

PAGE_LOAD_TIMEOUT = 45
ELEMENT_WAIT_TIMEOUT = 20
SCROLL_WAIT = 3


def get_driver():
    """Headless Chrome driver с маскировкой."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en']});
        """
    })
    return driver


def parse_product_card(card_element, base_url=BASE_URL, index=0):
    """Извлечение данных с подробным логированием."""
    try:
        print(f"  🔍 Парсинг карточки #{index+1}...")
        
        # 🔹 Название и ссылка
        title_elem = None
        for selector in [
            "a.product-title", ".product-name a", ".title a",
            "a[href*='/product/']", "a[href*='/catalog/']"
        ]:
            try:
                title_elem = card_element.find_element(By.CSS_SELECTOR, selector)
                if title_elem:
                    print(f"    ✅ Найдено название по селектору: {selector}")
                    break
            except:
                continue
        
        if title_elem:
            name = title_elem.text.strip() or title_elem.get_attribute("title") or ""
            product_url = title_elem.get_attribute("href")
            print(f"    📝 Название: '{name[:50]}{'...' if len(name)>50 else ''}'")
        else:
            # Фоллбэк: берём первый текст из карточки
            name = card_element.text.strip().split('\n')[0][:100]
            product_url = None
            print(f"    ⚠️ Название не найдено, используем фоллбэк: '{name}'")
        
        if not name or len(name) < 2:
            print(f"    ❌ Пропуск: слишком короткое название")
            return None
        
        # 🔹 Цена
        price = None
        for selector in [".price", ".product-price", ".cost", "[class*='price']"]:
            try:
                price_elem = card_element.find_element(By.CSS_SELECTOR, selector)
                price_text = price_elem.text.strip()
                match = re.search(r'(\d+\s?\d*)\s*₽', price_text)
                if match:
                    price = int(match.group(1).replace(' ', ''))
                    print(f"    💰 Цена: {price} ₽")
                    break
            except:
                continue
        if price is None:
            print(f"    ⚠️ Цена не найдена")
        
        # 🔹 Изображение (КРИТИЧНО: без изображения товар пропускается)
        image_url = None
        try:
            img = card_element.find_element(By.TAG_NAME, "img")
            for attr in ["data-src", "src", "data-lazy-src", "data-original"]:
                image_url = img.get_attribute(attr)
                if image_url:
                    print(f"    🖼️  Изображение ({attr}): {image_url[:60]}...")
                    break
            if image_url:
                if image_url.startswith("//"):
                    image_url = "https:" + image_url
                elif not image_url.startswith("http"):
                    image_url = base_url + image_url
        except NoSuchElementException:
            print(f"    ❌ Нет тега <img> в карточке")
        except Exception as e:
            print(f"    ❌ Ошибка получения изображения: {e}")
        
        if not image_url:
            print(f"    ❌ Пропуск: нет изображения")
            return None  # 🔑 Без изображения товар не публикуем
        
        # 🔹 Метаданные
        brand = None
        volume = None
        gender = None
        
        vol_match = re.search(r'(\d+(?:\.\d+)?\s*ml)', name, re.I)
        if vol_match:
            volume = vol_match.group(1).strip()
            print(f"    📦 Объем: {volume}")
        
        gender_match = re.search(r'\(([^)]*(женск|мужч|унисекс)[^)]*)\)', name, re.I)
        if gender_match:
            gender = gender_match.group(1).strip()
            print(f"    👤 Пол: {gender}")
        
        # Бренд
        parts = name.split()
        brand_parts = []
        for part in parts:
            if re.match(r'^[A-Z\s\-&]+$', part) and len(part) > 1:
                brand_parts.append(part)
            else:
                break
        brand = ' '.join(brand_parts) if brand_parts else None
        if brand:
            print(f"    🏷️ Бренд: {brand}")
        
        product_id = hashlib.md5(f"{name}{price}".encode()).hexdigest()[:12]
        
        print(f"    ✅ Карточка успешно распарсена!")
        
        return {
            "id": product_id,
            "name": name,
            "brand": brand,
            "price": price,
            "volume": volume,
            "gender": gender,
            "image_url": image_url,
            "product_url": product_url,
            "description": f"{name} - {price}₽" if price else name,
            "parsed_at": datetime.now().isoformat(),
            "pinterest_ready": False
        }
        
    except Exception as e:
        print(f"    ❌ Ошибка парсинга карточки: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_catalog_page(driver, url):
    """Парсинг страницы с отладкой."""
    try:
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.get(url)
        print(f"🌐 Страница загружена: {driver.title}")
    except TimeoutException:
        print(f"⚠️ Таймаут загрузки {url}")
        return []
    
    try:
        WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/product/'], .product-item, img"))
        )
    except TimeoutException:
        print("⚠️ Элементы не появились после ожидания")
        time.sleep(5)
    
    time.sleep(SCROLL_WAIT)
    
    # Прокрутка
    for _ in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
    
    products = []
    
    # Селекторы
    selectors = [
        "div.product-item", "div.catalog-item", "article.product",
        ".products-grid > div", ".catalog-grid > div",
        "div[data-product-id]", "div[class*='product']",
        "a[href*='/product/']"
    ]
    
    elements = []
    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if len(elements) > 0:
            print(f"✅ Найдено по селектору '{selector}': {len(elements)}")
            break
    
    if not elements:
        print("⚠️ Не найдено элементов, пробуем фоллбэк...")
        elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        print(f"🔍 Фоллбэк: найдено ссылок: {len(elements)}")
    
    print(f"\n🔄 Обрабатываю {len(elements)} элементов...")
    
    for i, elem in enumerate(elements[:10]):  # 🔹 Ограничим первые 10 для отладки
        if elem.tag_name == "a":
            try:
                container = elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'product') or contains(@class, 'item')]")
                product = parse_product_card(container, index=i)
            except:
                product = parse_product_card(elem, index=i)
        else:
            product = parse_product_card(elem, index=i)
        
        if product:
            products.append(product)
            print(f"  🎯 Добавлен товар: {product['name'][:40]}...\n")
        else:
            print(f"  ⏭️ Пропущен товар #{i+1}\n")
    
    # Удаляем дубликаты
    seen_urls = set()
    unique_products = []
    for p in products:
        if p.get("product_url") and p["product_url"] not in seen_urls:
            seen_urls.add(p["product_url"])
            unique_products.append(p)
    
    return unique_products


def save_json(data, filepath):
    """Сохранение в JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено: {filepath} ({len(data)} записей)")


def main():
    parser = argparse.ArgumentParser(description="Парсер DNK Parfum [ОТЛАДКА]")
    parser.add_argument("--url", default=f"{BASE_URL}/catalog", help="URL каталога")
    parser.add_argument("--pages", type=int, default=1, help="Количество страниц")
    parser.add_argument("--output", default="data/products.json", help="Выходной файл")
    
    args = parser.parse_args()
    
    driver = get_driver()
    all_products = []
    
    try:
        for page in range(1, args.pages + 1):
            url = args.url
            if page > 1:
                url = f"{args.url}?page={page}"
            
            print(f"\n{'='*60}")
            print(f"📄 Страница {page}/{args.pages}: {url}")
            print(f"{'='*60}\n")
            
            products = parse_catalog_page(driver, url)
            print(f"\n✅ Добавлено товаров: {len(products)}")
            all_products.extend(products)
            
            if page < args.pages:
                time.sleep(random.uniform(3, 6))
                
    finally:
        driver.quit()
    
    output_file = Path(args.output)
    save_json(all_products, output_file)
    
    with_images = len([p for p in all_products if p.get('image_url')])
    print(f"\n🎉 Готово!")
    print(f"📊 Всего товаров: {len(all_products)}")
    print(f"🖼️  С изображениями: {with_images}")


if __name__ == "__main__":
    main()
