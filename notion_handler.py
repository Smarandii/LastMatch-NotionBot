from datetime import datetime, timedelta
import os.path
from notion.client import NotionClient
from notion.block import SubsubheaderBlock, TextBlock, FileBlock, TodoBlock, NumberedListBlock, ColumnListBlock, \
    Block, CollectionViewBlock, DividerBlock, ImageBlock, EmbedOrUploadBlock
from notion.collection import CollectionRowBlock
from os import environ
from dotenv import load_dotenv
from os import path


class SearchProperties:

    def __init__(self, name="", t_type="", status="", date="", message=None):
        self.name = name
        self.t_type = t_type
        self.status = status
        self.date = date
        if message is not None:
            self.update_search_properties(message)

    def is_suitable(self, task: CollectionRowBlock):
        return (self.name in task.title or self.name == "") and (self.t_type in task.tip or self.t_type == "") \
               and (self.status in task.status or self.status == "") and (self.date in task.title or self.date == "")

    def update_search_properties(self, message):
        if "/name " in message.text:
            self.__setattr__("name", message.text.replace("/name ", ""))
        if "/type " in message.text:
            self.__setattr__("t_type", message.text.replace("/type ", ""))
        if "/status " in message.text:
            self.__setattr__("status", message.text.replace("/status ", ""))
        if "/date " in message.text:
            self.__setattr__("date", message.text.replace("/date ", "").capitalize())
        if "/search_name " in message.text:
            self.__setattr__("name", message.text.replace("/search_name ", ""))
        if "/search_type " in message.text:
            self.__setattr__("t_type", message.text.replace("/search_type ", ""))
        if "/search_status " in message.text:
            self.__setattr__("status", message.text.replace("/search_status ", ""))
        if "/search_date " in message.text:
            self.__setattr__("date", message.text.replace("/search_date ", ""))
        return self

    def __repr__(self):
        return f"Имя задачи содержит строку: {self.name}\n" \
               f"Тип задачи содержит строку: {self.t_type}\n" \
               f"Статус задачи содержит строку: {self.status}\n" \
               f"Дата задачи содержит строку: {self.date}\n"


class NotionHandler:
    NOTION_PAGE_URL = \
        "https://www.notion.so/smartspace/7dc7fe1fa5bc4cda8f286c7ea6ea1c2c?v=a4408676bda246f7bd1571134ef266a6"
    __REALIZED_BLOCKS = (SubsubheaderBlock, TextBlock, TodoBlock, FileBlock, NumberedListBlock, ColumnListBlock,
                         DividerBlock, CollectionViewBlock, ImageBlock, EmbedOrUploadBlock)
    __BOLD_SYMBOL_START = "*"
    __BOLD_SYMBOL_END = "*"
    __TODO_TRUE_SMBL = " ✅"
    __TODO_FALSE_SMBL = " ❌"
    __END_LINE_SMBL = "\n"
    __RESERVED_SMBLS = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    __RESERVED_SMBLS_W_BRACKETS = ['_', '*', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    def __init__(self, tg_id=None):
        self.tg_id = tg_id
        load_dotenv('.env')
        self.token_v2 = environ["token_v2"]
        self.client = NotionClient(self.token_v2)
        self.downloaded_files = []

    def delete_files(self):
        for file in self.downloaded_files:
            try:
                os.remove(file)
            except Exception:
                pass

    def __get_file_path(self, file_name: str) -> str:
        user_folder_path = path.join("download", str(self.tg_id))
        try:
            os.mkdir(user_folder_path)
        except FileExistsError:
            pass
        return path.join(user_folder_path, file_name)

    def __get_file_name(self, item: EmbedOrUploadBlock):
        pass

    def __download_file(self, item: EmbedOrUploadBlock, name):
        path = self.__get_file_path(name)
        item.download_file(path)
        self.downloaded_files.append(path)

    def __prepare_txt_4_md(self, txt: str) -> str:
        txt = str(txt)
        for smbl in self.__RESERVED_SMBLS:
            txt = txt.replace(smbl, "\\" + smbl)
        return txt

    def __prepare_txt_4_md_v2(self, txt: str) -> str:
        """
        This function replace only non brackets symbols.
        Brackets symbols is "()[]"
        :param txt:
        :return:
        """
        txt = str(txt)
        for smbl in self.__RESERVED_SMBLS_W_BRACKETS:
            txt = txt.replace(smbl, "\\" + smbl)
        return txt

    @staticmethod
    def __get_attrs_from_item_schema(item: CollectionRowBlock) -> dict:
        attrs = {}
        for dict_attr in item.schema:
            attrs.update({dict_attr["name"]: dict_attr["slug"]})
        return attrs

    def __divider_wrapper(self, item: DividerBlock) -> str:
        return self.__END_LINE_SMBL

    def __image_wrapper(self, item: ImageBlock):
        txt = self.__prepare_txt_4_md(f"{item.caption} img: {item.get_browseable_url()}")
        self.__download_file(item, name=item.file_id + ".jpg")
        return txt + self.__END_LINE_SMBL

    def __table_query_wrapper(self, item: CollectionRowBlock) -> str:
        txt = "\-\-\-\-\-\-\-\-\-\-" + self.__END_LINE_SMBL
        attrs = self.__get_attrs_from_item_schema(item)
        for name, slug in attrs.items():
            name = self.__prepare_txt_4_md(name)
            value = self.__prepare_txt_4_md(item.__getattr__(slug))
            txt += f"{name}: {value}" + self.__END_LINE_SMBL
            if value is None or value == "":
                txt = ""
                break
        return txt

    def __ss_header_wrapper(self, item: SubsubheaderBlock) -> str:
        return self.__txt_to_bold(item.title) + self.__END_LINE_SMBL * 2

    def __txt_wrapper(self, item: TextBlock) -> str:
        txt = self.__prepare_txt_4_md(item.title_plaintext)
        return txt + self.__END_LINE_SMBL * 2

    def __todo_wrapper(self, item: TodoBlock) -> str:
        txt = self.__prepare_txt_4_md(item.title_plaintext)
        if item.checked:
            txt += self.__TODO_TRUE_SMBL + self.__END_LINE_SMBL * 2
        else:
            txt += self.__TODO_FALSE_SMBL + self.__END_LINE_SMBL * 2
        return txt

    def __file_wrapper(self, item: FileBlock) -> str:
        txt = self.__prepare_txt_4_md(item.title + " url: " + item.get_browseable_url())
        print(f"downloading: {item.title}")
        self.__download_file(item, name=item.title)
        print(f"downloaded: {item.title}")
        return txt + self.__END_LINE_SMBL

    def __num_list_wrapper(self, item: NumberedListBlock) -> str:
        txt = self.__prepare_txt_4_md(item.title_plaintext)
        return txt + self.__END_LINE_SMBL

    def __collection_view_wrapper(self, item: CollectionViewBlock) -> str:
        txt = self.__prepare_txt_4_md(item.title)
        txt = self.__txt_to_bold(txt) + self.__END_LINE_SMBL
        for row in item.collection.get_rows():
            if row.title != "" or row.title is not None:
                txt += self.__table_query_wrapper(row)
        return txt

    def __item_is_used(self, item: Block) -> bool:
        return isinstance(item, self.__REALIZED_BLOCKS)

    def __txt_to_bold(self, txt: str) -> str:
        txt = self.__prepare_txt_4_md(txt)
        return f"{self.__BOLD_SYMBOL_START}{txt}{self.__BOLD_SYMBOL_END}"

    def __convert_2_txt_md(self, item: Block) -> str:
        """
        Function to convert Blocks from notion-py to markdown text using private class wrappers:
        __{block_name}_wrapper(item: Block) -> str:

        Function works only with Blocks that in __REALIZED_BLOCKS

        :param item:
        :return txt:
        """
        txt = ""
        if isinstance(item, SubsubheaderBlock):
            txt += self.__ss_header_wrapper(item)
        elif isinstance(item, TextBlock):
            txt += self.__txt_wrapper(item)
        elif isinstance(item, TodoBlock):
            txt += self.__todo_wrapper(item)
        elif isinstance(item, FileBlock):
            txt += self.__file_wrapper(item)
        elif isinstance(item, CollectionViewBlock):
            txt += self.__collection_view_wrapper(item)
        elif isinstance(item, DividerBlock):
            txt += self.__divider_wrapper(item)
        elif isinstance(item, NumberedListBlock):
            txt += self.__num_list_wrapper(item)
        elif isinstance(item, ImageBlock):
            txt += self.__image_wrapper(item)
        return txt

    def __unpack_block(self, block: Block) -> str:
        msg = ''
        for child in block.children:
            for child_inner in child.children:
                if self.__item_is_used(item=child_inner):
                    msg += self.__convert_2_txt_md(child_inner)
                else:
                    msg += self.__unpack_block(child_inner)
        return msg

    def __get_msg(self, task: CollectionRowBlock) -> str:

        self.downloaded_files = []
        msg = self.__get_task_header(task)
        for item in task.children:
            if self.__item_is_used(item):
                msg += self.__convert_2_txt_md(item)
            elif isinstance(item, ColumnListBlock):
                msg += self.__unpack_block(item)

            else:
                print(f"unknown instance: {type(item)} : {item.__repr__()}")

        return msg

    def get_tasks(self) -> tuple[str]:
        processed_tasks = tuple()
        main_page = self.client.get_block(self.NOTION_PAGE_URL)
        tasks = main_page.collection.get_rows()
        for task in tasks:
            task_msg = self.__get_msg(task)
            processed_tasks += tuple(task_msg)
            print(task_msg)
        return processed_tasks

    def get_task(self) -> str:
        main_page = self.client.get_block(self.NOTION_PAGE_URL)
        tasks = main_page.collection.get_rows()
        for task in tasks:
            task_msg = self.__get_msg(task)
            yield task_msg

    def get_new_task(self, task: CollectionRowBlock):
        new_task_txt = self.__txt_to_bold(f"Найдена новая задача!\nБыла создана: {task.created}\n")
        new_task_txt += self.__get_msg(task)
        return new_task_txt

    def find_tasks(self, search_prop: SearchProperties) -> str:
        main_page = self.client.get_block(self.NOTION_PAGE_URL)
        tasks = main_page.collection.get_rows()
        for task in tasks:
            if search_prop.is_suitable(task):
                task_msg = self.__get_msg(task)
                yield task_msg

    def new_task_available(self):
        print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] Checking if new task is available...")
        main_page = self.client.get_block(self.NOTION_PAGE_URL)
        latest_task = main_page.collection.get_rows()[0]
        when_created = latest_task.created
        now = datetime.now()
        diff = now - when_created
        if diff <= timedelta(hours=12):
            print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] FOUND {latest_task.id} {when_created}")
            return latest_task
        print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] NOT FOUND")
        return False

    def check_done_statuses(self):
        load_dotenv(".env")
        print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] Checking if done statuses in all tasks...")
        main_page = self.client.get_block(self.NOTION_PAGE_URL)
        for task in main_page.collection.get_rows():
            if task.created.month == datetime.now().month:
                if not ("DONE" in task.status):
                    print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] NOK")
                    return False
        print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] OK")
        return True

    def check_almst_done_statuses(self):
        counter = 0
        load_dotenv(".env")
        print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] Checking if almost done statuses in more than 4 tasks...")
        main_page = self.client.get_block(self.NOTION_PAGE_URL)
        for task in main_page.collection.get_rows():
            if "Почти" in task.status:
                counter += 1
            if environ["ALMOST_DONE_QUANTITY"] == str(counter):
                print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] OK")
                return True
        print(f"[{datetime.now().strftime('%d.%m.%y %H:%M:%S')}] NOK")
        return False

    def __get_task_header(self, task: CollectionRowBlock):
        title = self.__txt_to_bold(task.title) + self.__END_LINE_SMBL + self.__END_LINE_SMBL
        status = self.__txt_to_bold(task.status) + self.__END_LINE_SMBL
        t_type = self.__txt_to_bold(task.tip) + self.__END_LINE_SMBL
        return f"{title}{status}{t_type}"


if __name__ == "__main__":
    nh = NotionHandler()
    nh.check_done_statuses()
    for task in nh.get_tasks():
        print(task)
