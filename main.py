import time
import sys
import json
import random
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from openai import OpenAI

from secret import api_key

provider = "deepseek"
base_url = "https://api.deepseek.com/v1"
model_name = "deepseek-chat"

# --- 初始化 ---
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled") # 隐藏特征
options.add_experimental_option("excludeSwitches", ["enable-automation"])
driver = Chrome(options=options)
driver.get("https://onlineweb.zhihuishu.com/")

ai_client = OpenAI(api_key=api_key, base_url=base_url)

def random_sleep(min_s=0.6, max_s=1.1):
    time.sleep(random.uniform(min_s, max_s))

def check_CAPTCHA():
    try:
        time.sleep(0.5)
        driver.find_element(By.CLASS_NAME, "yidun_modal")
        input("出现验证码, 请手动完成后按回车键继续")
    except Exception:
        pass

def check() -> bool:
    try:
        if "课程问答" not in driver.title:
            print("检测到当前不在问答页, 正尝试在其他页面中查找问答页")
            all_windows = driver.window_handles
            for window in all_windows:
                driver.switch_to.window(window)  # 逐个窗口切换
                if "课程问答" in driver.title:
                    print("成功切换到课程问答页面")
                    return True
            else:
                print("未找到课程问答页面, 请打开课程问答页面")
                return False
        else:
            return True
    except Exception:  # 当前页已被关闭
        print("检测到当前不在问答页, 正尝试在其他页面中查找问答页")
        try:
            all_windows = driver.window_handles
        except Exception:  # driver已被关闭
            print("当前浏览器已被关闭, 程序无法继续执行, 正在退出")
            driver.quit()
            sys.exit(1)
        for window in all_windows:  # 逐个窗口找
            driver.switch_to.window(window)
            if "课程问答" in driver.title:
                print("成功切换到课程问答页面")
                return True
        else:
            print("未找到课程问答页面, 请打开课程问答页面")
            return False


def ask():
    if not check(): return
    wait = WebDriverWait(driver, 5) # 统一等待对象
    
    course_name = driver.find_element(By.CLASS_NAME, "course-name").text
    asks = int(input(f"课程: {course_name}\n请输入提问数量: "))
    
    question_elements = driver.find_elements(By.CLASS_NAME, "question-content")[:30]
    question_text = "\n".join([q.text for q in question_elements])
    
    ai_response = ai_client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "生成同领域相近问题，每行一个，无编号。"},
            {"role": "user", "content": f"基于以下例子生成{asks}个问题：\n{question_text}"},
        ],
        temperature=0.3,
    )
    questions_list = ai_response.choices[0].message.content.strip().split("\n")[:asks]
    for question in questions_list:
        # 点击提问按钮
        btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "ask-btn")))
        btn.click()
        
        # 输入并提交
        area = wait.until(EC.element_to_be_clickable((By.TAG_NAME, "textarea")))
        area.send_keys(question)
        check_CAPTCHA()
        
        random_sleep(0.5, 0.8) # 提交前的小随机
        # 调试: 打印页面所有按钮的class，找到正确的提交按钮选择器
        btns = driver.find_elements(By.TAG_NAME, "button")
        for b in btns:
            print(f"[DEBUG] button class='{b.get_attribute('class')}' text='{b.text}'")
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".up-btn.ZHIHUISHU_QZMD.set-btn")))
        submit.click()
        
        check_CAPTCHA()
        print(f"已提问: {question[:15]}...")
        random_sleep(1.0, 1.5) # 循环间隙稍长，防高频检测

def answer():
    if not check(): return
    wait = WebDriverWait(driver, 5)
    
    target_author = input("请输入目标提问者姓名: ").strip()
    target_count = int(input("目标完成数量 (个数): "))
    
    success_count = 0
    current_idx = 0 
    ori_page = driver.current_window_handle
    
    while success_count < target_count:
        items = driver.find_elements(By.CLASS_NAME, "question-item")
        
        # 自动滚动加载更多
        if current_idx >= len(items):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5) 
            items = driver.find_elements(By.CLASS_NAME, "question-item")
            if current_idx >= len(items): break # 彻底没题了

        current_item = items[current_idx]
        
        try:
            # 1. 快速匹配姓名
            if target_author not in current_item.text:
                current_idx += 1
                continue

            # 2. 匹配成功，进入详情页
            q_link = current_item.find_element(By.CLASS_NAME, "question-content")
            title = q_link.get_attribute("title")
            driver.execute_script("arguments[0].click();", q_link)
            
            wait.until(lambda d: len(d.window_handles) > 1)
            driver.switch_to.window([h for h in driver.window_handles if h != ori_page][-1])
            
            # 3. 极简回答逻辑
            local_wait = WebDriverWait(driver, 3)
            try:
                # 寻找按钮
                local_wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "my-answer-btn"))).click()
                txt_area = local_wait.until(EC.element_to_be_clickable((By.TAG_NAME, "textarea")))
                
                # 请求AI生成极简答案
                ai_res = ai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "直接回答问题，禁止废话，禁止编号，1-2句内。"},
                        {"role": "user", "content": title}
                    ],
                    temperature=0.2
                )
                ans_text = ai_res.choices[0].message.content.strip()
                
                # 填写并提交
                txt_area.send_keys(ans_text)
                check_CAPTCHA()
                random_sleep(0.6, 1.0)
                local_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".up-btn.ZHIHUISHU_QZMD.set-btn"))).click()
                check_CAPTCHA()
                
                success_count += 1
                print(f"[{success_count}/{target_count}] 成功回答: {title[:10]}...")
            except:
                pass # 已回答则跳过
            
            driver.close()
            driver.switch_to.window(ori_page)
            current_idx += 1
            random_sleep(0.8, 1.2)

        except Exception:
            current_idx += 1
            if len(driver.window_handles) > 1: driver.close()
            driver.switch_to.window(ori_page)


def main():
    while True:
        print("\n选择模式: [1]提问 [2]回答 [3]退出程序(浏览器也会关闭)")
        mode = input("Input Mode: ")
        match mode:
            case "1":
                ask()
            case "2":
                answer()
            case "3":
                driver.quit()
                return
            case _:
                print("请输入正确的选项")


if __name__ == "__main__":
    main()
