import re
import time
import pymysql

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys


class InstagramBot:

    def __init__(self, user_login, password_login):
        self.username = user_login
        self.password = password_login
        self.driver = webdriver.Firefox()

    def closeBrowser(self):
        self.driver.close()

    def login(self):
        driver = self.driver
        driver.get("https://www.instagram.com/")
        time.sleep(2)
        login_button = driver.find_element_by_xpath("//a[@href='/accounts/login/?source=auth_switcher']")
        login_button.click()
        time.sleep(2)
        user_name_elem = driver.find_element_by_xpath("//input[@name='username']")
        user_name_elem.clear()
        user_name_elem.send_keys(self.username)
        password_elem = driver.find_element_by_xpath("//input[@name='password']")
        password_elem.clear()
        password_elem.send_keys(self.password)
        password_elem.send_keys(Keys.RETURN)
        time.sleep(2)

    def gather_photos(self, link):
        driver = self.driver
        driver.get(link)
        time.sleep(2)

        # gathering photos
        pic_hrefs = []
        # it will scroll 7 times to load more pics
        for i in range(1, 7):
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                # get tags
                hrefs_in_view = driver.find_elements_by_tag_name('a')
                # finding relevant hrefs
                hrefs_in_view = [elem.get_attribute('href') for elem in hrefs_in_view
                                 if '.com/p/' in elem.get_attribute('href')]
                # building list of unique photos
                [pic_hrefs.append(href) for href in hrefs_in_view if href not in pic_hrefs]
                print("Check: pic href length " + str(len(pic_hrefs)))
            except Exception:
                pass
        return pic_hrefs

    def get_comments(self, post_id):
        # trying to use the post id as primary key in the database but after a while ig will change the id
        photo_id = post_id[-12:-1]
        # connect to database
        cnx = pymysql.connect(user='root', password='',
                              host='127.0.0.1',
                              database='ig_comments')
        cursor = cnx.cursor()
        cursor.execute("SELECT id FROM user_comments")
        fotos_existentes = cursor.fetchall()
        # check if the post was already at the db (probably not working)
        if photo_id in fotos_existentes:
            return False
        self.driver.get(post_id)
        time.sleep(1)
        # load more comments if button exists
        try:
            # clicking 3 times on the more comments button
            for i in range(0, 3):
                button_elem = self.driver.find_element_by_xpath("//li//button[@type='button']")
                button_elem.click()
                time.sleep(2)
        except NoSuchElementException:
            pass

        time.sleep(1)

        try:
            comments_block = self.driver.find_element_by_xpath('//article//ul/..')
            comments_in_block = comments_block.find_elements_by_xpath("//li//h3/..")
            comments = [x.find_element_by_tag_name('span').text for x in comments_in_block]
            without_tagged_user_comments = []
            # dropping tagged responses (might be unrelated to the user comment)
            for comment in comments:
                if "@" not in comment:
                    without_tagged_user_comments.append(comment)

            # getting the user comment #todo re-think this
            user_comment_elem = comments_block.find_elements_by_xpath("//ul//li[1]//span")
            try:
                if len(user_comment_elem) < 1:
                    user_comment = ""
                else:
                    user_comment = re.sub(r'#.\w*', '', user_comment_elem[0].text)
                # Checking if a user_comment has responses to store in the db
                if len(comments) > 0:
                    if "'" in user_comment:
                        user_comment = user_comment.replace("'", "''")
                    cursor.execute(
                        "INSERT INTO user_comments (id,comment) VALUES ('%s','%s')" % (photo_id, user_comment))
                    cnx.commit()
                    for respuesta in without_tagged_user_comments:
                        if "'" in respuesta:
                            respuesta = respuesta.replace("'", "''")
                        cursor.execute(
                            "INSERT INTO responses (id_user_comments,response) VALUES ('%s','%s')" % (
                            photo_id, respuesta))
                        cnx.commit()
                    cnx.close
            except Exception:
                pass
        except NoSuchElementException:
            return False
        return True


# log in info for ig
username = "USERNAME"
password = "PASSWORD"
ig = InstagramBot(username, password)
ig.login()
# here you can add links, could be hashtags or igprofiles
links = ['https://www.instagram.com/explore/tags/love/',
         'https://www.instagram.com/zuck/'
         ]
for u in links:
    photos = ig.gather_photos(u)
    for j in range(0, len(photos)):
        ig.get_comments(photos[j])
        if "/explore/tags/" in u:
            print("Tag " + u[39:-1])
        else:
            print("User "+u[26:-1])
        print("Photo %d/%d" % ((j+1), len(photos)))

ig.closeBrowser()
