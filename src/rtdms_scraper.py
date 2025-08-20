import datetime
import pandas as pd
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

STATION_DROPDOWN_XPATH = '/html/body/app-root/div/app-apps/nz-layout/app-sidebar-menu/nz-layout/nz-layout/nz-layout/nz-content/app-average-report/div[1]/div/nz-layout/div/div/nz-layout/nz-content/div[2]/app-reports-filter/div[1]/form/div/div[10]/nz-form-control/div/div/nz-select/nz-select-top-control'

def apply_category_filter(wait, category_text="Textile"):
    try:
        category_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, '//input[@aria-label="Category Filter Input"]')))
        category_input.clear()
        category_input.send_keys(category_text)
        category_input.send_keys(Keys.ENTER)
        print(f"✅ Category filter applied: {category_text}")
        time.sleep(3)
    except Exception as e:
        print(f"❌ Could not apply category filter '{category_text}': {e}")

def scroll_to_load_all(wait, driver, prev_count):
    action_buttons_xpath = '//div[@col-id="action"]//span[contains(@class, "actions_btn")]'
    scrolled = prev_count
    no_change = 0
    while True:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(2)
        new_actions = driver.find_elements(By.XPATH, action_buttons_xpath)
        if len(new_actions) > scrolled:
            scrolled = len(new_actions)
            no_change = 0
        else:
            no_change += 1
        if no_change >= 3:
            break
    return scrolled

def set_dates(wait, driver, from_str, to_str):
    try:
        date_inputs = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, '//input[@placeholder="Select date"]'))
        )
        if len(date_inputs) < 2:
            print("❌ Could not find both Start/End date inputs!")
            return False
        from_date_input = date_inputs[0]
        to_date_input = date_inputs[1]
        driver.execute_script("arguments[0].value = ''", from_date_input)
        from_date_input.send_keys(from_str)
        from_date_input.send_keys(Keys.TAB)
        time.sleep(0.3)
        driver.execute_script("arguments[0].value = ''", to_date_input)
        to_date_input.send_keys(to_str)
        to_date_input.send_keys(Keys.TAB)
        time.sleep(0.3)
        print(f"✅ Date set: {from_str} to {to_str}")
        return True
    except Exception as e:
        print(f"❌ Failed to set date range: {e}")
        return False

def get_all_station_options(wait, driver):
    try:
        station_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, STATION_DROPDOWN_XPATH)))
        station_dropdown.click()
        time.sleep(0.4)
    except Exception:
        print("❌ Station dropdown did not appear! Skipping this industry row.")
        driver.find_element(By.TAG_NAME, 'body').click()
        return []
    for _ in range(12):
        try:
            options_area = wait.until(EC.visibility_of_element_located((By.XPATH, '//nz-option-container')))
            options_area.send_keys(Keys.END)
            time.sleep(0.1)
        except Exception:
            break
    options = driver.find_elements(By.XPATH, '//nz-option-container//nz-option-item/div')
    station_names = []
    found_set = set()
    for opt in options:
        label = opt.text.strip()
        if label and label not in found_set:
            station_names.append(label)
            found_set.add(label)
    driver.find_element(By.TAG_NAME, 'body').click()
    return station_names

def select_station_by_name_puppeteer_style(wait, driver, station_name):
    try:
        station_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, STATION_DROPDOWN_XPATH)))
        station_dropdown.click()
        time.sleep(0.4)
    except Exception as e:
        print(f"❌ Could not click station select box: {e}")
        return False
    for _ in range(12):
        options = driver.find_elements(By.XPATH, '//nz-option-container//nz-option-item/div')
        for opt in options:
            if opt.text.strip() == station_name:
                opt.click()
                time.sleep(0.4)
                print(f"✅ Selected station: {station_name}")
                return True
        try:
            options_area = wait.until(EC.visibility_of_element_located((By.XPATH, '//nz-option-container')))
            options_area.send_keys(Keys.END)
            time.sleep(0.1)
        except Exception:
            break
    print(f"❌ Could not find station '{station_name}' after scrolling.")
    driver.find_element(By.TAG_NAME, 'body').click()
    return False

def select_all_parameters(wait, driver):
    try:
        params_input = wait.until(EC.element_to_be_clickable((
            By.XPATH, '/html/body/app-root/div/app-apps/nz-layout/app-sidebar-menu/nz-layout/nz-layout/nz-layout/nz-content/app-average-report/div[1]/div/nz-layout/div/div/nz-layout/nz-content/div[2]/app-reports-filter/div[1]/form/div/div[11]/nz-form-control/div[1]/div/nz-select/nz-select-top-control/nz-select-search/input'
        )))
        params_input.click()
        time.sleep(0.3)
        try:
            options_area = WebDriverWait(driver, 2).until(EC.presence_of_element_located((
                By.XPATH, '//div[contains(@class,"ant-select-dropdown") and contains(@style,"display: block")]'
            )))
            for _ in range(12):
                options_area.send_keys(Keys.END)
                time.sleep(0.1)
        except Exception:
            pass
        try:
            param_option_divs = wait.until(EC.presence_of_all_elements_located((
                By.XPATH, '//nz-option-item//div[contains(@class,"ant-select-item-option-content")]'
            )))
        except Exception:
            print("❌ No parameters found in this station. Moving to next.")
            driver.find_element(By.TAG_NAME, 'body').click()
            return False
        if not param_option_divs:
            print("❌ No parameters found in this station. Moving to next.")
            driver.find_element(By.TAG_NAME, 'body').click()
            return False
        count_clicked = 0
        for div in param_option_divs:
            try:
                if div.is_displayed():
                    div.click()
                    time.sleep(0.05)
                    count_clicked += 1
            except Exception:
                continue
        print(f"✅ Selected all parameters by clicking {count_clicked} items.")
        driver.find_element(By.TAG_NAME, 'body').click()
        time.sleep(0.2)
        return True
    except Exception as e:
        print(f"❌ Failed to select all parameters: {e}")
        return False

def go_back_to_main_list(wait, driver):
    try:
        back_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, '//button[contains(translate(text(),"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"), "back") or contains(translate(text(),"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"), "cancel") or contains(@class,"back") or contains(@class,"cancel") or contains(@aria-label,"back") or contains(@aria-label,"close") or @role="button"]'
        )))
        back_btn.click()
        print("🔙 Clicked Back button to return to main list.")
        time.sleep(1)
    except Exception:
        print("⚠ No Back button found, trying browser back.")
        driver.back()
        time.sleep(1)

def switch_to_grid_mode(wait, driver):
    try:
        grid_button = wait.until(EC.element_to_be_clickable((
            By.XPATH, '//button[span[text()="Grid"]]'
        )))
        if "activeButton" not in grid_button.get_attribute("class"):
            grid_button.click()
            print("✅ Switched to Grid mode.")
            time.sleep(1)
        else:
            print("ℹ Already in Grid mode.")
    except Exception as e:
        print(f"❌ Could not switch to Grid mode: {e}")

def scrape_grid_table(driver, plant_label="PLANT", station_label="STATION", week_start="", week_end="", industry_info_dict=None):
    time.sleep(1)
    try:
        table_div = driver.find_element(
            By.XPATH, '/html/body/app-root/div/app-apps/nz-layout/app-sidebar-menu/nz-layout/nz-layout/nz-layout/nz-content/app-average-report/div[1]/div/nz-layout/div[2]/div/nz-layout/nz-content/div/div[2]/div[4]/div/div/app-grid-view/div'
        )
        table = table_div.find_element(By.XPATH, './/table')
        headers = [th.text.strip() for th in table.find_elements(By.XPATH, ".//thead//th")]
        data_rows = []
        for tr in table.find_elements(By.XPATH, ".//tbody//tr"):
            row = [td.text.strip() for td in tr.find_elements(By.XPATH, "./td")]
            row_full = [plant_label, station_label, week_start, week_end]
            if industry_info_dict:
                row_full += [industry_info_dict.get(k, "") for k in sorted(industry_info_dict.keys())]
            row_full += row
            data_rows.append(row_full)
        full_headers = ["Plant", "Station", "Range_From", "Range_To"]
        if industry_info_dict:
            full_headers += list(sorted(industry_info_dict.keys()))
        full_headers += headers
        if data_rows:
            print(f"🌟 GRID SCRAPE SUCCESSFUL 🌟 {len(data_rows)} rows, {len(headers)} columns")
        else:
            print("⚠ Table found but no rows present.")
        return pd.DataFrame(data_rows, columns=full_headers)
    except Exception as e:
        print(f"ℹ No table found in grid view for week {week_start} to {week_end}: {e}")
        return pd.DataFrame()

def ensure_all_15min_intervals(df, from_str, to_str, timestamp_col="Date & Time", fill_value=0):
    t_start = pd.to_datetime(from_str)
    t_end = pd.to_datetime(to_str) + pd.Timedelta(days=1) - pd.Timedelta(minutes=15)
    full_times = pd.date_range(t_start, t_end, freq="15min")
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
    df = df.set_index(timestamp_col)
    df = df.reindex(full_times, fill_value=fill_value)
    df = df.reset_index().rename(columns={'index': timestamp_col})
    return df

def run_scraping_for_all_weeks(wait, driver, plant_label, station_label, industry_info_dict, all_dataframes):
    start_date = datetime.date(2024, 12, 1)
    end_of_month = datetime.date(2024, 12, 31)
    last_headers = None
    got_real_data = False
    first_batch = True
    dfs_this_station = []
    while start_date <= end_of_month:
        end_date = start_date + datetime.timedelta(days=6)
        if end_date > end_of_month:
            end_date = end_of_month
        from_str = start_date.strftime('%Y/%m/%d')
        to_str = end_date.strftime('%Y/%m/%d')
        print(f"🗓  Scraping from {from_str} to {to_str}")

        if not set_dates(WebDriverWait(driver, 10), driver, from_str, to_str):
            print(f"❌ Skipping this week for station due to date setting failure.")
            start_date = end_date + datetime.timedelta(days=1)
            first_batch = False
            continue

        try:
            view_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH, '/html/body/app-root/div/app-apps/nz-layout/app-sidebar-menu/nz-layout/nz-layout/nz-layout/nz-content/app-average-report/div[1]/div/nz-layout/div/div/nz-layout/nz-content/div[2]/app-reports-filter/div[2]/button[1]'
            )))
            view_btn.click()
            print("✅ Clicked View/Search button.")
            time.sleep(1.5)
        except Exception as e:
            print(f"❌ Failed to click View/Search button: {e}")
            start_date = end_date + datetime.timedelta(days=1)
            first_batch = False
            continue
        switch_to_grid_mode(wait, driver)
        df = scrape_grid_table(driver, plant_label, station_label, from_str, to_str, industry_info_dict)
        if not df.empty and 'Date & Time' in df.columns:
            df = ensure_all_15min_intervals(df, from_str, to_str, timestamp_col='Date & Time', fill_value=0)
            print(f"Including all 15-min intervals for this week, rows now: {len(df)}")
        if not df.empty:
            last_headers = df.columns.tolist()
            got_real_data = True
            dfs_this_station.append(df)
        else:
            if got_real_data and last_headers:
                dummy_row = [plant_label, station_label, from_str, to_str]
                if industry_info_dict:
                    for k in sorted(industry_info_dict.keys()):
                        dummy_row.append(industry_info_dict[k])
                ncols = len(last_headers) - len(dummy_row)
                dummy_row += [0]*ncols
                dummy_df = pd.DataFrame([dummy_row], columns=last_headers)
                dfs_this_station.append(dummy_df)
                print(f"➖ No data for this range; added zeros row for this batch.")
            elif first_batch:
                print(f"⏭ No data present for first week. Skipping this station.")
                return False
        start_date = end_date + datetime.timedelta(days=1)
        first_batch = False
    if got_real_data and dfs_this_station:
        all_dataframes.extend(dfs_this_station)
        return True
    return False

def get_industry_info_from_row(driver, i):
    try:
        name = driver.find_element(By.XPATH, f'(//div[@row-index="{i}"])[1]/div[@col-id="industryName"]').text.strip()
    except Exception:
        name = ""
    return {"Industry Name": name}

# -------------- Main script -----------------

if __name__ == "__main__":
    # make category selection work in both Jupyter and CLI
    category_to_use = "Textile"
    try:
        if "ipykernel" in sys.modules or "jupyter" in sys.modules:
            # In notebook: just use default or set above
            print(f"Notebook detected. Using category '{category_to_use}'.")
        else:
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument('--category', type=str, default="Textile", help="Category to filter (e.g., Textile, Chemical)")
            # the next line fixes usage in Jupyter too:
            args, unknown = parser.parse_known_args()
            category_to_use = args.category
    except Exception as ex:
        print(f"Couldn't parse command line args, defaulting category to '{category_to_use}'.")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    all_dataframes = []

    driver.get("https://rtdms.cpcb.gov.in/publicdata/#/l/public-data")

    try:
        apply_category_filter(wait, category_to_use)
        scrolled = scroll_to_load_all(wait, driver, 0)
        action_cells = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@col-id="action"]')))
        action_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@col-id="action"]//span[contains(@class, "actions_btn")]')))
        row_count = len(action_buttons)
        processed_rows = 0

        for i in range(row_count):
            apply_category_filter(wait, category_to_use)
            action_cells = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@col-id="action"]')))
            action_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@col-id="action"]//span[contains(@class, "actions_btn")]')))
            print(f"➡ Trying row {i+1} of {row_count}")
            try:
                industry_info = get_industry_info_from_row(driver, i)
                plant_label = industry_info.get("Industry Name", f"Plant_{i+1}")
                actions = ActionChains(driver)
                actions.move_to_element(action_cells[i]).click(action_buttons[i]).perform()
                print(f"✅ Clicked 'View' on row {i+1}.")
                time.sleep(2)
                station_names = get_all_station_options(wait, driver)
                print(f"Found Stations: {station_names}")

                for idx, station_name in enumerate(station_names):
                    if idx != 0:
                        print("🔄 Reloading page for new station selection...")
                        driver.refresh()
                        wait = WebDriverWait(driver, 20)
                        time.sleep(3)
                    if not select_station_by_name_puppeteer_style(wait, driver, station_name):
                        print(f"Skipping station: {station_name}")
                        continue
                    if not select_all_parameters(wait, driver):
                        print(f"No parameters in station: {station_name}, skipping to next station.")
                        continue
                    had_data = run_scraping_for_all_weeks(wait, driver, plant_label, station_name, industry_info, all_dataframes)
                    if not had_data:
                        print(f"No data for ANY week in {station_name}, skipping.")
                go_back_to_main_list(wait, driver)
            except Exception as e:
                print(f"❌ Error processing row {i+1}: {e}")
                go_back_to_main_list(wait, driver)
                continue

        if all_dataframes:
            final_df = pd.concat(all_dataframes, ignore_index=True)
            final_df.to_excel("scraped_textile_results_15min.xlsx", index=False)
            print(f"✅ All results saved: {len(final_df)} rows in 'scraped_textile_results_15min.xlsx'")
        else:
            print("❌ No data found to save.")

    except Exception as e:
        print(f"❌ Critical error: {e}")

    finally:
        driver.quit()

