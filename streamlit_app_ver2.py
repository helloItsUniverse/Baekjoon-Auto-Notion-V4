import streamlit as st
import requests
import datetime
import openai
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from langs import langs

# (if nessesary) adjusts UTC offset (minus 9 hours)
def adjust_datetime_offset():
    time_Here_Now = datetime.datetime.now()
    time_UTC_Now = datetime.datetime.utcnow()
    timediff = time_Here_Now - time_UTC_Now
    date_string = (datetime.datetime.now() - timediff).strftime("%Y-%m-%d %H:%M:%S")
    return date_string

# refactor page id to let notion API understand
def refactor_page_id(input_page_id):
    return input_page_id[: 8] + '-' + input_page_id[8 : 12] + '-' + input_page_id[12 : 16] + '-' + input_page_id[16 : 20] + '-' + input_page_id[20 :]

# constructs database properties(json type) to use as payload data for 'post' request
def json_input(parent_page_id):
    parent_value = {'type': 'page_id', 'page_id': parent_page_id}
    
    # date_string = adjust_datetime_offset() # 데이터베이스 제목에 적혀 있는 시간이 현재 시간보다 9시간 빠르게 되어 있다면 이 줄을 사용할 것
    date_string = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 데이터베이스 제목에 적혀 있는 시간이 현재 시간보다 9시간 빠르게 되어 있다면 이 줄을 주석처리할 것
    title_value = [{'type': 'text', 'text': {'content': f'{date_string}', 'link': None}}]
    icon_value = {'emoji': '🖥️', 'type': 'emoji'}

    tier_property = {
        'Tier': {
            'name': 'Tier',
            'type': 'files',
            'files': {}
        }
    }

    language_property = {
        'Language': {
            'name': 'Language',
            'select': {},
            'type': 'select'
        }
    }

    date_property = {
        'Date': {
            'name': 'Date',
            'type': 'date',
            'date': {}
        }
    }

    category_property = {
        'Category': {
            'name': 'Category',
            'multi_select': {
                'options': []
            },
            'type': 'multi_select'
        }
    }

    title_property = {
        'Title': {
            'id': 'title',
            'name': 'Title',
            'title': {},
            'type': 'title'
        }
    }
    
    properties_value = {}
    properties_value.update(tier_property)
    properties_value.update(language_property)
    properties_value.update(date_property)
    properties_value.update(category_property)
    properties_value.update(title_property)
    
    return [parent_value, icon_value, title_value, properties_value]

# creates database with prepared json data
def create_database(data: dict, notion_token):
    parent = data[0]
    icon = data[1]
    title = data[2]
    properties = data[3]
    
    create_url = "https://api.notion.com/v1/databases/"
    
    # headers
    headers = {
        "Authorization": "Bearer " + notion_token,
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",  # Check what is the latest version here: https://developers.notion.com/reference/changes-by-version
    }
    
    payload = {
        "parent": parent,
        "icon": icon,
        "title": title,
        "properties": properties}
    
    response = requests.post(create_url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"{response.status_code}: Database created successfully\n")
        con.text(f"{response.status_code}: Database created successfully")
    else:
        print(f"{response.status_code}: Error during database creation")
        con.text(f"{response.status_code}: Error during database creation")
        
    response_database_id = response.json()["id"]
    # file_path = 'database_id.txt'
    # try:
    #     with open(file_path, 'w') as f:
    #         f.truncate()
    #         f.write(response_database_id)
    # except IOError:
    #     print('\nFile open failure!\n')
    return response

# ======================================================================
# crawling resources
def code_comments(param):
    try:
        # print('\nChatGPT(ver 3.5-turbo) is now generating code comments ...')
        con.text('ChatGPT(ver 3.5-turbo) is now generating code comments ...')
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'system', 'content': ''},
                {'role': 'user', 'content': "다음 코드의 작동 원리를 간결하게 한글로 설명해라 (말투는  \"~이다\"): " + param}
            ],
            temperature=0.4
        )
    except:
        print("OpenAI API Error!")
        return
    return response['choices'][0]['message']['content']

def get_problem(prob_n):
    url = "https://solved.ac/api/v3/problem/show"
    querystring = {"problemId": str(prob_n)}
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers, params=querystring)
    except:
        print("Solved.ac API ERROR!")
        return
    data = response.json()
    problemId = data['problemId']
    titleKo = data['titleKo']
    level = data['level']
    tags = [tag['displayNames'][0]['name'] for tag in data['tags']]
    return [problemId, titleKo, level, tags]

def get_code(code_link):
    with requests.Session() as session:

        r = session.get(code_link, headers=headers_user_agent)
        soup = BeautifulSoup(r.text,'html.parser')

        h1_tag = soup.find('h1', class_="pull-left")
        a_tag = h1_tag.find('a', href=lambda x: x and '/problem/' in x)

        if a_tag:
            href_value = a_tag['href']
            problem_number = href_value.split('/')[-1]

        textarea_tag = soup.find('textarea', {'class': 'form-control no-mathjax codemirror-textarea'})
        if textarea_tag:
            source_code = textarea_tag.text
        
        divs = soup.find_all('div', {'class': 'col-md-12'})

        for div in divs:
            headline_tag = div.find('div', {'class': 'headline'})
            if headline_tag:
                h2_tag = headline_tag.find('h2')
                if h2_tag:
                    lang = h2_tag.text
                    code_lang = langs[lang]

        tds = soup.find_all('td', {'class': 'text-center'})
        info = []
        for td in tds:
            info.append(td.text)
        extra_info=info[1:]
        extra_info[0]=extra_info[0]+'KB'
        extra_info[1]=extra_info[1]+'ms'
        extra_info[2]=extra_info[2]+'B'

        return [problem_number, code_lang, source_code, extra_info]





# create columns(attributes) preset of database properties
def create_properties(problem_info, submit_info):
    title = str(problem_info[0]) + ' - ' + problem_info[1]
    date_string = adjust_datetime_offset()
    icon_value = {'type': 'external',
        'external': {
            'url': f'https://d2gd6pc034wcta.cloudfront.net/tier/{str(problem_info[2])}.svg'
        }
    }
    properties = {
        'Date': create_attr_date(date_string),
        'Language': create_attr_language(submit_info[1]),
        'Category': create_attr_multiselect(problem_info[3]),
        'Title': create_attr_title(title),
        'Tier': create_attr_tier(problem_info[2]),
    }
    return properties, icon_value

def create_attr_date(date_string):
    return {
        'id': 'NRBf',
        'type': 'date',
        'date': {
            'start': date_string,
            'end': None,
            'time_zone': None
        }
    }

def create_attr_language(language_name):
    return {
        'id': 'WSy%5C',
        'type': 'select',
        'select': {
            'name': language_name,
        }
    }

def create_attr_multiselect(tags):
    multiselect_tags = []
    tag_dict = {}
    for tag in tags:
        tag_dict['name'] = tag
        multiselect_tags.append(tag_dict)
        tag_dict = {}
    return {
        'id': 'mLa%5D',
        'type': 'multi_select',
        'multi_select': multiselect_tags
    }

def create_attr_title(title):
    return {
        'id': 'title',
        'type': 'title',
        'title': [
            {
            'type': 'text',
            'text': {
                'content': title,
                'link': None
            },
            'annotations': {
                'color': 'default'
            },
            'plain_text': title,
            'href': None,
            
            }           
        ]
    }
    
def create_attr_tier(tier_num):
    return {
        'id': 'euHl',
        'type': 'files',
        'files': [
            {
                'name': f'https://d2gd6pc034wcta.cloudfront.net/tier/{str(tier_num)}.svg',
                'type': 'external',
                'external': {
                    'url': f'https://d2gd6pc034wcta.cloudfront.net/tier/{str(tier_num)}.svg'
                }
            }
        ]
    }





# (request.post) create empty page with preset
def create_page(data, DATABASE_ID):
    properties = data[0]
    icon = data[1]
    create_url = "https://api.notion.com/v1/pages"
    payload = {"parent": {"database_id": DATABASE_ID}, "properties": properties, "icon": icon}
    
    res = requests.post(create_url, headers=headers, json=payload)
    if res.status_code == 200:
        print(f"{res.status_code}: Page created successfully")
        con.text(f"{res.status_code}: Page created successfully")
    else:
        print(f"{res.status_code}: Error during page creation")
        con.text(f"{res.status_code}: Error during page creation")
    return res

# create blocks inside of page
def create_blocks(problem_info, submit_info, GPT_comments):
    return {
    "children": [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        'href': f'https://www.acmicpc.net/problem/{problem_info[0]}',
                        'plain_text': '문제 링크',
                        'text': {'content': '문제 링크',
                            'link': {'url': f'https://www.acmicpc.net/problem/{problem_info[0]}'}},
                        "type": "text",
                    }
                ]
            },
        }, 
        {
            "callout": {
                'color': 'gray_background',
                'icon': {'emoji': '💡', 'type': 'emoji'},
                "rich_text": [
                    {
                        'href': None,
                        'plain_text': '/'.join(problem_info[3]),
                        'text': {'content': '/'.join(problem_info[3]),
                            'link': None},
                        "type": "text",
                    }
                ]
            },
            "object": "block",
            "type": "callout",
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": []
            },
        },
        {
            'object': 'block',
            'quote': {'color': 'default',
                'rich_text': [
                    {
                        'annotations': {'bold': True},
                        'href': None,
                        # 'plain_text': f"{'Memory   '+submit_info[3][0]:<50}{'Time   '+submit_info[3][1]:^0}{'Code Length   '+submit_info[3][2]:>50}",
                        'plain_text': f'Memory   {submit_info[3][0]}\nTime   {submit_info[3][1]}\nCode Length   {submit_info[3][2]}',
                        'text': 
                            {
                                'content': f'Memory   {submit_info[3][0]}\nTime   {submit_info[3][1]}\nCode Length   {submit_info[3][2]}',
                                'link': None
                            },
                        'type': 'text'
                    }
                ]
            },
            'type': 'quote'
        }, 
        {
            'code': 
                {
                    'caption': [],
                    'language': submit_info[1],
                    'rich_text': [
                        {
                            'annotations': {'color': 'default'},
                            'href': None,
                            'plain_text': submit_info[2],
                            'text': {
                                'content': submit_info[2],
                                'link': None
                                },
                            'type': 'text'
                        }
                    ]
                },
            'object': 'block',
            'type': 'code'
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        'href': None,
                        'plain_text': GPT_comments,
                        'text': {'content': GPT_comments,
                            'link': None},
                        "type": "text",
                    }
                ]
            },
        },
    ],
}

# (request.patch) edit(fill) page with blocks
def edit_page(page_block_id, data: dict):
    edit_url = f"https://api.notion.com/v1/blocks/{page_block_id}/children"
    payload = data
    res = requests.patch(edit_url, headers=headers, json=payload)
    if res.status_code == 200:
        print(f"{res.status_code}: Page edited successfully")
        con.text(f"{res.status_code}: Page edited successfully")
    else:
        print(f"{res.status_code}: Error during page editing")
        con.text(f"{res.status_code}: Error during page editing")
    return res


# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================

st.set_page_config(layout="wide")

st.title("BOJ-to-Notion Auto Uploader :sunglasses:")

col1, col2 = st.columns(2)

with col1:
    input_parent_page_id = st.text_input(label='# 1. Please input your Parent Page ID', value="")
    input_database_id = st.text_input(label='# 2. (Auto-generate) Your Database ID', value="")
    input_openai_key = st.text_input(label='# 3. Please input your OpenAI key', type='password', value="")
    input_notion_secret = st.text_input(label='# 4. Please input your Notion API Secret Key', type='password', value="")
    input_code_share_link = st.text_input(label="# 5. BOJ Source Code Share Link", value="")
    
    btn_clicked = st.button("Submit to Notion")



# headers
headers = {
    "Authorization": "Bearer " + input_notion_secret,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",  # Check what is the latest version here: https://developers.notion.com/reference/changes-by-version
}

# create user_agent for data scraping
ua = UserAgent()
user_agent = ua.random
headers_user_agent = {
    'User-Agent': user_agent
}

openai.api_key = input_openai_key

with col2:

    if btn_clicked:
        con = st.container()
        con.caption("Result")
        if not str(input_parent_page_id) \
            or not str(input_openai_key) \
            or not str(input_notion_secret) \
            or not str(input_code_share_link):
            con.error("Something is empty. Check your inputs again")
        else:
            # con.write(f"Your Parent Page ID is: {str(input_parent_page_id)}  \n\
            #     Your OpenAI key is: {str(input_openai_key)}   \n\
            #     Your Notion Secret Key is: {str(input_notion_secret)}  \n\
            #     Your BOJ Share Code Link is: {str(input_code_share_link)}  \n")
            
            if not str(input_database_id):
                con.text('database does not exist!')
                response_database = create_database(json_input(refactor_page_id(input_parent_page_id)), input_notion_secret)
                
                submit_info = get_code(input_code_share_link)
                problem_info = get_problem(submit_info[0])
                GPT_comments = code_comments("\n".join(submit_info[2]))
                response_page = create_page(create_properties(problem_info, submit_info), input_database_id)
                page_block_id = response_page.json()["id"]
                blocks = create_blocks(problem_info, submit_info, GPT_comments)
                edit_page(page_block_id, blocks)
            
            else:
                con.text('database already exists!  \n')
                
                submit_info = get_code(input_code_share_link)
                problem_info = get_problem(submit_info[0])
                GPT_comments = code_comments("\n".join(submit_info[2]))
                response_page = create_page(create_properties(problem_info, submit_info), input_database_id)
                page_block_id = response_page.json()["id"]
                blocks = create_blocks(problem_info, submit_info, GPT_comments)
                edit_page(page_block_id, blocks)
            
            
            
            
            # # print('\nreading database properties ...')
            # con.text('reading database properties ...')
            # # print('\ncreating new page row ...\n')
            # con.text('creating new page row ...')
            # response = create_page(create_properties(problem_info, submit_info), input_database_id)

            # # get page block id
            # page_block_id = response.json()["id"]

            # # fill the page with blocks(using block id)
            # blocks = create_blocks(problem_info, submit_info, GPT_comments)
            # edit_page(page_block_id, blocks)