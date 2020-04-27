import json
import time
import math
import random

from urllib import parse
from library.constants import Method
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

from library.decorators import retry, check_execute
from library.base_class.spider import BaseSpider
from library.constants import TimeFMT, Injected_JS
from crawlers.taobaoke.lib.constants import UrlFormat, TableName, SpiderName, ProjectName


class GoodListSpider(BaseSpider):
    def __init__(self):
        super(GoodListSpider, self).__init__()
        self.project_name = ProjectName.PROJECT_NAME
        self.spider_name = SpiderName.Good_List
        self.status = False
        self.token = ''
        self.login_cookie = ''
        self.data_form = {
            '0': ',"usertype":1',                                          # 天猫
            '1': ',"service":"jhs"',                                     # 聚划算
            '2': ',"auction_tag":"513"',                                # 天猫超市
            '3': ',"service":"dpyhq"',                                   # 优惠券
            '4': ',"service":"myf"',                                       # 包邮
            '5': ',"service":"jpmj"',                                  # 金牌卖家
            '6': ',"service":"xfzbz"',                                  # 消费者保证
            '7': ',"service":"yxjh"',                                  # 营销计划
            '8': ',"tk_group_tag":10101,"tk_scene":"content"',          # 内容商品库
            '9': ',"auction_tag":"87490"',                                # 淘抢购
            '10': ',"auction_tag":"14401,71682"'                          # 海淘
        }
        self.api_info = {
            'page': 0,
            'topage': 1,
            'max_id': '',
            'has_next': True
        }

    def spider_config(self, value):
        """
        爬虫配置信息，包括url、headers、proxies、verify
        :return:
        """
        try:
            if self.status is not False:
                self.api_info['page'] += 1
                self.api_info['topage'] += 1
            _time = time.time()*1000
            _time = math.floor(_time)
            _time = str(_time)
            url = UrlFormat.RECOMMEND_LIST_URL.format(_time=_time, token=self.token)
            data = f'''{{"floorId":"20392","pageNum":{self.api_info['page']},"pageSize":60,"refpid":"mm_232870043_0_0","variableMap":{{"fn":"search","toPage":{self.api_info['topage']}{value}}}}}'''
            data = parse.quote(data)
            _data_ = '_data_=' + data
            headers = {
                'authority': 'pub.alimama.com',
                'method': 'POST',
                'path': f'/openapi/json2/1/gateway.unionpub/optimus.material.json?t={_time}&_tb_token_={self.token}',
                'scheme': 'https',
                'accept': '*/*',
                'accept-encoding': 'gzip,deflate,br',
                'accept-language': 'zh-CN,zh;q=0.9',
                'content-length': '122',
                'cookie': self.login_cookie,
                'origin': 'https://pub.alimama.com',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'referer': 'https://pub.alimama.com/promo/search/index.htm?spm=a219t.11816995.1998910419.de727cf05.2a8f75a54z8NZI',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
                'x-requested-with': 'XMLHttpRequest'
            }
            # headers, proxies = self.get_proxies(proxies_type=1, headers=headers, space_time=1, failed_time=30)
            return {
                'url': url,
                'headers': headers,
                'timeout': 60,
                # 'proxies': proxies,
                'data': _data_
            }
        except Exception as e:
            print(e)
            return None

    @retry()
    def get_and_check_response(self, method: str = 'GET', spider_config: dict = None):
        """
        get和check response即是：获取并且正确的response
        :param method: http response 的方法
        :param spider_config: 爬虫配置信息
        :return:
        """
        response = super().get_response(method=method, spider_config=spider_config)
        return self.check_response(response)

    def check_response(self, response):
        """
        判断获取的response数据是否正确。因为api接口会一直返回200，但是数据不一定正确。html可以通过状态码验证
        :param response:
        :return: 返回bool
        """
        if not response:
            return response
        try:
            json_data = json.loads(response.text)
            if 'httpStatusCode' not in json_data:
                return False
            code = json_data['httpStatusCode']
            if code == 200:                                         # http 请求成功
                try:
                    if json_data['success'] is False:
                        self.api_info['has_next'] = False           # 是否有下一页
                    # self.api_info['page'] += 1
                except Exception as e:
                    print(e)
                    self.api_info['has_next'] = False
                return response
            else:
                return False
        except Exception as e:
            print(e)
            return False

    def parse(self, response, key):
        if not response:
            return response
        data_list = list()
        try:
            json_data = json.loads(response.text)
            if json_data['success'] is False:
                return
            result_list = json_data['model']['recommend']['resultList']
            for item in result_list:
                if 'couponAmount' in item:
                    data_list.append(
                        {
                            'service': key,
                            'cal_tk_commission': float(item['calTkCommission'])*100,             # 佣金
                            'item_id': item['itemId'],                                           # 商品id
                            'item_name': item['itemName'],                                       # 商品名
                            'month_sell_count': item['monthSellCount'],                          # 月销量
                            'price': float(item['price'])*100,                                   # 原价
                            'coupon_amount': float(item['couponAmount'])*100,                    # 优惠券面值
                            'coupon_remain_count': item['couponRemainCount'],                    # 优惠券剩余数量
                            'coupon_send_count': item['couponSendCount'],                        # 优惠券发放数量
                            'couponTotalCount': item['couponTotalCount'],                        # 优惠券总数
                            'price_after_coupon': float(item['priceAfterCoupon'])*100,           # 折后价
                            'shop_id': item['sellerId'],                                         # 卖家id
                            'shop_title': item['shopTitle'],                                     # 店铺名称
                            'origin_data': json.dumps(item, ensure_ascii=False)                  # 元数据
                        }
                    )
                else:
                    data_list.append(
                        {
                            'service': key,
                            'cal_tk_commission': float(item['calTkCommission']) * 100,  # 佣金
                            'item_id': item['itemId'],  # 商品id
                            'item_name': item['itemName'],  # 商品名
                            'month_sell_count': item['monthSellCount'],  # 月销量
                            'price': float(item['price']) * 100,  # 原价
                            'price_after_coupon': float(item['priceAfterCoupon']) * 100,  # 折后价
                            'shop_id': item['sellerId'],  # 卖家id
                            'shop_title': item['shopTitle'],  # 店铺名称
                            'origin_data': json.dumps(item, ensure_ascii=False)  # 元数据
                        }
                    )

            return data_list
        except Exception as e:
            print(e)
            return False

    @check_execute(ProjectName.PROJECT_NAME, SpiderName.Recommend_List, ['xhaibin@zhiyitech.cn'])
    def execute(self):
        for key, value in self.data_form.items():
            self.api_info = {
                'page': 0,
                'topage': 1,
                'max_id': '',
                'has_next': True
            }
            while self.api_info['has_next']:
                spider_config = self.spider_config(value=value)                                             # 配置爬虫信息
                response = self.get_and_check_response(method=Method.POST, spider_config=spider_config)     # http请求验证
                if not response:
                    self.get_cookies()
                    continue
                data_list = self.parse(response=response, key=key)                                     # 解析

                self.status = self.insert_or_update(table_name=TableName.TBK_GOOD_LIST,                # 更新数据
                                                    data_list=data_list)                                    # 更新商品是否有效
                time.sleep(random.uniform(1.0, 5.0))
        return self.status

    def get_cookies(self):
        """通过selenium 获取cookie"""
        url = 'https://www.alimama.com/member/login.htm'
        # headers, proxies = self.get_proxies(proxies_type=2, headers=None, space_time=1, failed_time=30, http='https')
        try:
            chrome_options = Options()
            # chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument("–proxy-server=42.51.13.69:21080")
            chrome_options.add_argument('--user-data-dir=/Users/zy/Library/Application Support/Google/Chrome')
            driver = webdriver.Chrome(chrome_options=chrome_options)
            # driver.execute_script(Injected_JS)            # 清除selenium标记
            time.sleep(random.uniform(2, 3))
            driver.get(url=url)
            time.sleep(2)
            # driver.execute_script(Injected_JS)            # 清除selenium标记
            driver.switch_to_frame("taobaoLoginIfr")
            time.sleep(2)
            flag = driver.find_element_by_xpath('//a[@class="forget-pwd J_Quick2Static"]').text
            if flag:                                        # 判断元素是否存在
                driver.find_element_by_xpath('//a[@class="forget-pwd J_Quick2Static"]').click()
            time.sleep(2)
            driver.find_element_by_id("TPL_username_1").clear()
            # driver.find_element_by_id("TPL_password_1").clear()
            driver.find_element_by_id('TPL_username_1').send_keys(u'162316546')
            # driver.execute_script(Injected_JS)            # 清除selenium标记
            time.sleep(random.uniform(2, 4))
            driver.find_element_by_id('TPL_password_1').send_keys('465456')
            time.sleep(random.uniform(1, 3))
            flag = driver.find_element_by_xpath('//div[@id="nc_1__scale_text"]/span').text
            if flag:
                self.slider_validation(driver)
            time.sleep(random.uniform(2, 4))
            driver.find_element_by_id('J_SubmitStatic').click()
            time.sleep(3)
            driver.refresh()
            time.sleep(5)
            cookie_list = driver.get_cookies()
            cookie = ''
            for item in cookie_list:
                cookie = cookie + item['name'] + '=' + item['value'] + ';'
                if item['name'] == '_tb_token_':
                    self.token = item['value']
            cookie = cookie.strip(';')
            self.login_cookie = cookie
            print(cookie_list)
            print(cookie)
            driver.refresh()  # 刷新页面
            time.sleep(1)
            return
        except Exception as e:
            print(e)

    def slider_validation(self, driver):
        builder = ActionChains(driver)
        l = driver.find_element_by_id("nc_1_n1z")       # 获取滑块元素
        builder.reset_actions()             # 清除之前的action
        track = self.move_mouse(250)       # 计算滑块移动的轨迹，250为移动距离
        builder.move_to_element(l)          # 移动到滑块所在位置
        builder.click_and_hold()            # 点击左键不释放
        time.sleep(0.2)
        for i in track:                     # 开始生成移动轨迹
            builder.move_by_offset(xoffset=i, yoffset=0)
            builder.reset_actions()
        time.sleep(3)
        builder.release().perform()       # 释放左键，执行for中的操作
        builder.release()

    def move_mouse(self, distance):            # 鼠标移动
        remaining_dist = distance
        moves = [30]
        a = 0
        while remaining_dist > 0:    # 鼠标移动距离不断加大
            span = random.randint(30, 40)
            a += span
            moves.append(a)
            remaining_dist -= span
            if sum(moves[:-1]) > 200:
                print(sum(moves))
                break
        return moves


def main():
    spider = GoodListSpider()
    spider.get_cookies()
    spider.execute()


if __name__ == '__main__':
    main()
