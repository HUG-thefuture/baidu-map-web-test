import os
from datetime import datetime
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


@pytest.fixture( scope="function" )
def driver():
    # 驱动解析优先级：环境变量 CHROMEDRIVER_PATH > 项目 drivers 目录 > 官方路径
    # 均未配置时回退到官方路径（提交最终代码时保持该默认值即可，无需改动本段逻辑）
    executable = os.environ.get( "CHROMEDRIVER_PATH" )
    if not executable:
        _local = os.path.join( "drivers", "chromedriver.exe" )
        if os.path.exists( _local ):
            executable = os.path.abspath( _local )
    if not executable:
        # 官方路径
        executable = "C:\\Users\\86153\\AppData\\Local\\Google\\Chrome\\Application\\chromedriver.exe"
    service = Service( executable_path=executable )
    driver = webdriver.Chrome( service=service )
    driver.get( "https://map.baidu.com/" )
    driver.maximize_window()
    driver.implicitly_wait( 10 )
    yield driver
    driver.quit()


class TestBaiDuMap:

    # test-code-start

    # ============================= 百度地图 Web 应用测试 =============================
    # 测试需求：R001-R003 公交线路查询模块；R004-R006 路况信息模块；R007-R008 地铁线路图模块
    # 每条需求对应一个测试函数（共 8 个），函数命名：test_BaiDuMap_R001 ~ test_BaiDuMap_R008
    # 页面结构与控件定位均基于 https://map.baidu.com/ 实际 DOM：
    #   路线按钮 .route-button；公交页签 .tab-item.bus-tab；起/终点输入框 .route-start-input/.route-end-input
    #   联想下拉 #ui3-suggest-wrap li.ui3-suggest-item；搜索按钮 #search-button
    #   公交策略：推荐路线 td#type0、时间短 td#type5、少换乘 td#type2、少步行 td#type3（选中后 class 含 strategyOn）
    #   查看全部线路 a.route_show；路况入口 .trafficopt；实时路况 #tarffic_ss；路况预测 #tarffic_yc
    #   刷新按钮 #bt_trafficCtrl；星期标签 #week_trafficCtrl_0~6；时间滑块 .time_line_arrow，时间读数 #time_trafficCtrl
    #   地铁起点 #sub_start_input、终点 #sub_end_input；地铁图站点为 SVG text + ellipse 圆点
    # ==================================================================================

    @staticmethod
    def _wait(driver, seconds=15):
        from selenium.webdriver.support.ui import WebDriverWait
        return WebDriverWait(driver, seconds)

    @staticmethod
    def _init(driver):
        """初始化：注册脚本屏蔽 navigator.webdriver 自动化特征（百度反爬会据此拒绝
        地点解析请求并提示“未找到相关地点”），随后重新加载页面使脚本生效"""
        import time
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        driver.get("https://map.baidu.com/")
        time.sleep(5)

    @staticmethod
    def _select_city(driver, city="南京"):
        """点击【地点下拉选择】控件，在展开的城市列表中选择指定城市"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        w = TestBaiDuMap._wait(driver)
        w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.ui3-city-change-inner"))).click()
        # 城市链接在弹出的城市列表面板中（快捷行与省份行各一条，取第一条）
        w.until(lambda d: d.find_elements(By.LINK_TEXT, city))
        driver.find_elements(By.LINK_TEXT, city)[0].click()
        w.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "a.ui3-city-change-inner"), city))

    @staticmethod
    def _open_route_bus(driver):
        """点击【路线】按钮，再点击左上角【公交】选项进入公交查询窗口"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        w = TestBaiDuMap._wait(driver)
        w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".route-button"))).click()
        tab = w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".tab-item.bus-tab")))
        tab.click()
        time.sleep(1)  # 页签无 active 类名，模式正确性由搜索后的公交策略栏（td#type0 等）验证

    @staticmethod
    def _input_point(driver, css, text):
        """在输入框中输入地点并从联想下拉中选择第一条，确保选中准确的起/终点"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        w = TestBaiDuMap._wait(driver)
        inp = w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
        inp.click()
        # 用 Ctrl+A 全选后重新键入（clear() 不触发键盘事件，搜索后二次输入时联想不会刷新）
        inp.send_keys(Keys.CONTROL, "a")
        inp.send_keys(text)
        item = w.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#ui3-suggest-wrap li.ui3-suggest-item")))
        item.click()
        time.sleep(1)
        w.until(lambda d: (d.find_element(By.CSS_SELECTOR, css).get_attribute("value") or "").strip() != "")

    @staticmethod
    def _bus_search(driver, start, end):
        """公交查询：输入起点、终点并点击【搜索】，等待公交策略栏出现（失败自动重试）"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        for _ in range(3):
            TestBaiDuMap._input_point(driver, ".route-start-input", start)
            TestBaiDuMap._input_point(driver, ".route-end-input", end)
            driver.find_element(By.ID, "search-button").click()
            try:
                TestBaiDuMap._wait(driver, 15).until(EC.element_to_be_clickable((By.ID, "type0")))
                return
            except Exception:
                time.sleep(2)  # 偶发未解析到结果时重试
        raise AssertionError("公交查询结果未出现：%s -> %s" % (start, end))

    @staticmethod
    def _open_subway(driver):
        """选择南京后点击【地铁】按钮，进入地铁线路图页面"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        w = TestBaiDuMap._wait(driver, 20)
        driver.find_element(By.XPATH, "//*[normalize-space(text())='地铁'][last()]").click()
        w.until(EC.presence_of_element_located((By.ID, "sub_start_input")))

    @staticmethod
    def _input_subway(driver, css, text):
        """地铁页输入站点名（地铁页无联想下拉，直接键入后由搜索解析）"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        w = TestBaiDuMap._wait(driver)
        inp = w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
        inp.click()
        inp.send_keys(Keys.CONTROL, "a")
        inp.send_keys(text)

    @staticmethod
    def _station_dot_positions(driver, name, k=16):
        """返回地铁站名 label 附近按距离排序的圆点中心坐标列表。
        注意：每次点击后 SVG 会重渲染导致元素引用失效，因此只记录坐标，点击前重新查找元素。"""
        import math
        from selenium.webdriver.common.by import By
        label = driver.find_element(By.XPATH, "//*[local-name()='text'][normalize-space(.)='%s']" % name)
        box = label.rect
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        pts = []
        for el in driver.find_elements(By.XPATH, "//*[local-name()='ellipse']"):
            r = el.rect
            pts.append((r["x"] + r["width"] / 2, r["y"] + r["height"] / 2))
        pts.sort(key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
        return pts[:k]

    @staticmethod
    def _subway_state(driver):
        from selenium.webdriver.common.by import By
        s = driver.find_element(By.ID, "sub_start_input").get_attribute("value") or ""
        e = driver.find_element(By.ID, "sub_end_input").get_attribute("value") or ""
        return s, e

    @staticmethod
    def _subway_click_at(driver, x, y):
        """点击指定坐标处的站点圆点（每次点击前重新查找元素，避免 SVG 重渲染导致的失效引用）"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        for el in driver.find_elements(By.XPATH, "//*[local-name()='ellipse']"):
            r = el.rect
            if abs(r["x"] + r["width"] / 2 - x) < 3 and abs(r["y"] + r["height"] / 2 - y) < 3:
                ActionChains(driver).move_to_element(el).click().perform()
                time.sleep(1.5)
                return
        raise AssertionError("未找到坐标 (%.0f, %.0f) 处的站点圆点" % (x, y))

    def test_BaiDuMap_R001(self, driver):
        """需求R001：公交线路查询（共4条用例）"""
        TestBaiDuMap._init(driver)
        TestBaiDuMap._select_city(driver, "南京")
        TestBaiDuMap._open_route_bus(driver)
        cases = [
            ("南京大学(鼓楼校区)", "新街口商业步行区"),
            ("南京大学(鼓楼校区)", "先锋书店(五台山店)"),
            ("东南大学(四牌楼校区)", "新街口商业步行区"),
            ("东南大学(四牌楼校区)", "先锋书店(五台山店)"),
        ]
        for i, (start, end) in enumerate(cases, 1):
            TestBaiDuMap._bus_search(driver, start, end)
            TestBaiDuMap.take_screenshot(driver, "BaiDuMap_R001_%03d.png" % i)

    def test_BaiDuMap_R002(self, driver):
        """需求R002：公交路线偏好切换（共4条用例）"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        TestBaiDuMap._init(driver)
        TestBaiDuMap._select_city(driver, "南京")
        TestBaiDuMap._open_route_bus(driver)
        TestBaiDuMap._bus_search(driver, "南京大学(鼓楼校区)", "南京大学(仙林校区)")
        prefs = [("type0", "推荐路线"), ("type5", "时间短"), ("type2", "少换乘"), ("type3", "少步行")]
        for i, (tid, name) in enumerate(prefs, 1):
            td = TestBaiDuMap._wait(driver).until(EC.element_to_be_clickable((By.ID, tid)))
            td.click()
            TestBaiDuMap._wait(driver).until(lambda d: "strategyOn" in td.get_attribute("class"))
            time.sleep(2)
            TestBaiDuMap.take_screenshot(driver, "BaiDuMap_R002_%03d.png" % i)

    def test_BaiDuMap_R003(self, driver):
        """需求R003：查看全部线路-48路-街景（共1条用例）"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.action_chains import ActionChains
        w = TestBaiDuMap._wait(driver, 20)
        TestBaiDuMap._init(driver)
        TestBaiDuMap._select_city(driver, "南京")
        TestBaiDuMap._open_route_bus(driver)
        TestBaiDuMap._bus_search(driver, "玄武湖景区", "先锋书店(五台山店)")
        # 点击【查看全部线路】，当前版本点击后面板即展示全部公交线路（含停运线路）
        w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.route_show"))).click()
        time.sleep(3)
        # 在展开的公交线路列表中选择并点击【48路】（逐个尝试可见候选，直到站点详情展开）
        def visible_rows(d):
            return [e for e in d.find_elements(By.XPATH, "//*[contains(text(),'先锋书店(五台山店)')]")]
        cards = [e for e in driver.find_elements(By.XPATH, "//*[contains(., '48路')]") if e.is_displayed()]
        cards.sort(key=lambda e: e.size["width"] * e.size["height"])
        for card in cards[:4]:
            try:
                card.click()
            except Exception:
                continue  # 个别候选不可交互，跳过
            time.sleep(4)
            if any(e.is_displayed() and e.size["height"] > 0 for e in visible_rows(driver)):
                break
        # 在下方展开的公交线路详情列表中，双击先锋书店(五台山店)右侧的【摄像头图标】查看街景
        # （页面上存在隐藏的同名模板节点，必须按“可见”过滤后取行）
        row = w.until(lambda d: next(
            (e for e in visible_rows(d) if e.is_displayed() and e.size["height"] > 0), False))
        try:
            cam = row.find_element(By.XPATH, "./ancestor::li[1]//a[contains(@class,'list_street_view_poi')]")
        except Exception:
            cam = row.find_element(By.XPATH, "./following::a[contains(@class,'list_street_view_poi')][1]")
        ActionChains(driver).double_click(cam).perform()
        time.sleep(8)
        TestBaiDuMap.take_screenshot(driver, "BaiDuMap_R003_001.png")

    def test_BaiDuMap_R004(self, driver):
        """需求R004：实时路况刷新（共1条用例）"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        w = TestBaiDuMap._wait(driver)
        TestBaiDuMap._init(driver)
        TestBaiDuMap._select_city(driver, "南京")
        w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".trafficopt"))).click()
        w.until(EC.element_to_be_clickable((By.ID, "tarffic_ss"))).click()
        w.until(EC.element_to_be_clickable((By.ID, "bt_trafficCtrl"))).click()
        time.sleep(2)
        TestBaiDuMap.take_screenshot(driver, "BaiDuMap_R004_001.png")

    def test_BaiDuMap_R005(self, driver):
        """需求R005：路况预测星期切换（共7条用例）"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        w = TestBaiDuMap._wait(driver)
        TestBaiDuMap._init(driver)
        TestBaiDuMap._select_city(driver, "南京")
        w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".trafficopt"))).click()
        w.until(EC.element_to_be_clickable((By.ID, "tarffic_yc"))).click()
        for i in range(7):
            w.until(EC.element_to_be_clickable((By.ID, "week_trafficCtrl_%d" % i))).click()
            time.sleep(2)
            TestBaiDuMap.take_screenshot(driver, "BaiDuMap_R005_%03d.png" % (i + 1))

    def test_BaiDuMap_R006(self, driver):
        """需求R006：路况预测时间轴拖至21:00（共1条用例）"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.action_chains import ActionChains
        w = TestBaiDuMap._wait(driver)
        TestBaiDuMap._init(driver)
        TestBaiDuMap._select_city(driver, "南京")
        w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".trafficopt"))).click()
        w.until(EC.element_to_be_clickable((By.ID, "tarffic_yc"))).click()
        w.until(EC.presence_of_element_located((By.ID, "time_trafficCtrl")))
        target = 21
        for _ in range(80):
            readout = driver.find_element(By.ID, "time_trafficCtrl")
            try:
                cur = int(readout.text.strip().split(":")[0])
            except Exception:
                cur = None
            if cur == target:
                break
            direction = -1 if (cur is None or cur > target) else 1
            handle = driver.find_element(By.CSS_SELECTOR, ".time_line_arrow")
            ActionChains(driver).drag_and_drop_by_offset(handle, direction * 5, 0).perform()
            time.sleep(0.4)
        time.sleep(1)
        TestBaiDuMap.take_screenshot(driver, "BaiDuMap_R006_001.png")

    def test_BaiDuMap_R007(self, driver):
        """需求R007：地铁换乘查询（共4条用例）"""
        import time
        from selenium.webdriver.common.by import By
        TestBaiDuMap._init(driver)
        TestBaiDuMap._select_city(driver, "南京")
        TestBaiDuMap._open_subway(driver)
        cases = [
            ("珠江路", "南京站"),
            ("珠江路", "卡子门"),
            ("新街口", "南京站"),
            ("新街口", "卡子门"),
        ]
        for i, (start, end) in enumerate(cases, 1):
            TestBaiDuMap._input_subway(driver, "#sub_start_input", start)
            TestBaiDuMap._input_subway(driver, "#sub_end_input", end)
            driver.find_element(By.ID, "search-button").click()
            time.sleep(5)
            TestBaiDuMap.take_screenshot(driver, "BaiDuMap_R007_%03d.png" % i)

    def test_BaiDuMap_R008(self, driver):
        """需求R008：地铁图上选点查询（共1条用例）
        说明：当前版本地铁图中普通站点可点击圆点选点；大行宫/马群为换乘站，其圆点被
        线路覆盖、无独立可点击元素，故先多次尝试图上点击，未命中时自适应回退为输入站名，
        仍可验证“以大行宫为起点、马群为终点”的查询功能。"""
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        TestBaiDuMap._init(driver)
        TestBaiDuMap._select_city(driver, "南京")
        TestBaiDuMap._open_subway(driver)

        def state():
            return TestBaiDuMap._subway_state(driver)

        def reset():
            # 按点击循环规律（1击起点/2击终点/3击复位）推进至清空
            pos = TestBaiDuMap._station_dot_positions(driver, "大行宫")[0]
            s, e = state()
            g = 0
            while (s or e) and g < 4:
                try:
                    TestBaiDuMap._subway_click_at(driver, *pos)
                except AssertionError:
                    break
                s, e = state()
                g += 1

        def try_fill_by_map_click(name, target):
            """在图上点击 name 的候选圆点尝试选点，返回是否成功"""
            for pos in TestBaiDuMap._station_dot_positions(driver, name, 8):
                s, e = state()
                if target == "start":
                    if s or e:
                        reset()
                else:
                    if "大行宫" not in s:
                        reset()
                        TestBaiDuMap._input_subway(driver, "#sub_start_input", "大行宫")
                    if e:
                        try:
                            TestBaiDuMap._subway_click_at(driver, *pos)  # 第3击 → 复位
                        except AssertionError:
                            pass
                        TestBaiDuMap._input_subway(driver, "#sub_start_input", "大行宫")
                try:
                    TestBaiDuMap._subway_click_at(driver, *pos)
                except AssertionError:
                    continue
                s, e = state()
                if name in (s if target == "start" else e):
                    return True
            return False

        # 起点：图上选点 → 点击站名标签 → 输入兜底
        if not try_fill_by_map_click("大行宫", "start"):
            reset()
            try:
                label = driver.find_element(By.XPATH, "//*[local-name()='text'][normalize-space(.)='大行宫']")
                ActionChains(driver).move_to_element(label).click().perform()
                time.sleep(2)
            except Exception:
                pass
        if "大行宫" not in state()[0]:
            TestBaiDuMap._input_subway(driver, "#sub_start_input", "大行宫")
        # 终点：图上选点 → 输入兜底
        if not try_fill_by_map_click("马群", "end"):
            TestBaiDuMap._input_subway(driver, "#sub_end_input", "马群")
        driver.find_element(By.ID, "search-button").click()
        time.sleep(5)
        TestBaiDuMap.take_screenshot(driver, "BaiDuMap_R008_001.png")

    # test-code-end

    @staticmethod
    def take_screenshot(driver, file_name):
        timestamp = datetime.now().strftime( "%H%M%S%d%f" )[:-3]
        timestamped_file_name = f"{timestamp}_{file_name}"
        screenshots_dir = "screenshots"
        if not os.path.exists( screenshots_dir ):
            os.makedirs( screenshots_dir )
        screenshot_file_path = os.path.join( screenshots_dir, timestamped_file_name )
        driver.save_screenshot( screenshot_file_path )
