#-*- coding: utf8 -*-
import logging
import json
import grab
import codecs
import html2text

from grab.spider import Spider, Task
from grab.selector import XpathSelector as Selector
from lxml.html import fromstring
from lxml import etree

WEEKDAYS = {
            u"Пн": 1,
            u"Вт": 2,
            u"Ср": 3,
            u"Чт": 4,
            u"Пт": 5,
            u"Сб": 6,
            u"Нд": 7,
           }

def parseSubjectTable(html):
    sel = Selector(fromstring(html))
    subjects = {}

    h2t = html2text.HTML2Text()
    h2t.bypass_tables = True
    h2t.ignore_emphasis = True

    for weekid,elem in enumerate(sel.select("//table//tr")):
        subjectSel = Selector(fromstring(elem.html()))
        oneSubject = []
        for subgroupid,subgroup in enumerate(subjectSel.select("//td")):
            subject = subgroup.html()
            subgroupSel = Selector(fromstring(subject))
            div = subgroupSel.select("//div")
            if div.count() == 0:
                oneSubject.append({})
            else:
                subject_content = h2t.handle(div.html())
                subject = [line.strip() for line in subject_content.split("\n") if line]
                assert len(subject) == 3
                oneSubject.append({"name": subject[0], "teacher": subject[1], "room": subject[2]})
        subjects["week{}".format(weekid)] = oneSubject

    return subjects

class LPSpider(Spider):
    BASE = "http://www.lp.edu.ua/node/40"
    initial_urls = [BASE]

    def prepare(self):
        super(LPSpider, self).prepare()

    def shutdown(self):
        super(LPSpider, self).shutdown()

    def task_initial(self, grab, task):
        for inst in grab.doc.select('//select[@name="inst"]/option'):
            if not inst.text(): continue
            inst_name, inst_attr = inst.text(), inst.attr("value")
            yield Task("inst",
                inst_name=inst_name, inst_attr=inst_attr,
                url="{}?inst={}&group=&semestr=0&semest_part=1".format(LPSpider.BASE, inst_attr))

    def task_inst(self, grab, task):
        logging.info("Fetching institute ".format(task.inst_name))
        for group in grab.doc.select('//select[@name="group"]/option'):
            if not group.text(): continue
            group_name, group_attr = group.text(), group.attr("value")
            yield Task("group",
                inst_name=task.inst_name, inst_attr=task.inst_attr,
                group_name=group_name, group_attr=group_attr,
                url="{}?inst={}&group={}&semestr=0&semest_part=1".format(LPSpider.BASE, task.inst_attr, group_attr))

    def task_group(self, grab, task):
        for semestr in ["0", "1"]:
            for semest_part in ["1", "2"]:
                yield Task("parse",
                        inst_name=task.inst_name, inst_attr=task.inst_attr,
                        group_name=task.group_name, group_attr=task.group_attr,
                        semestr=semestr, semest_part=semest_part,
                        url="{}?inst={}&group={}&semestr={}&semest_part={}".format(LPSpider.BASE, task.inst_attr,
                            task.group_attr, semestr, semest_part))

    def task_parse(self, grab, task):
        logging.info(u"Parse {} {} {} {}".format(task.inst_name, task.group_name, task.semestr, task.semest_part))

        schedule = {}
        for tr in grab.doc.select('//div[@id="stud"]/table/tr'):
            sel = Selector(fromstring(tr.html()))

            if sel.select("./td").count() == 0:
                continue

            if sel.select("./td").count() == 1:
                dayweek = WEEKDAYS[sel.select("./td").text()]
                continue

            if sel.select("./td").count() == 2:
                number = sel.select("./td")[0].text()
                html = sel.select("./td")[1].html()

            if sel.select("./td").count() == 3:
                dayweek = WEEKDAYS[sel.select("./td")[0].text()]
                number = sel.select("./td")[1].text()
                html = sel.select("./td")[2].html()

            schedule[dayweek] = schedule.get(dayweek, {})
            schedule[dayweek][number] = parseSubjectTable(html)
        if schedule:
            with codecs.open(u"out/{}-{}-{}-{}.json".format(task.inst_name, task.group_name, task.semestr, task.semest_part), "w", encoding='utf-8') as out:
                json.dump(schedule, out, ensure_ascii=False)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    bot = LPSpider(thread_number=1)
    #bot.setup_queue(backend="mongo", database="tvtropes-grab")
    bot.run()

    # g = grab.Grab()
    # g.go("http://www.lp.edu.ua/node/40?inst=7&group=6980&semestr=0&semest_part=1")
    # dayweek = None
    # schedule = {}
    # for tr in g.doc.select('//div[@id="stud"]/table/tr'):
    #     sel = Selector(fromstring(tr.html()))
    #     if sel.select("./td").count() == 1:
    #         dayweek = WEEKDAYS[sel.select("./td").text()]
    #     if sel.select("./td").count() == 2:
    #         number = sel.select("./td")[0].text()
    #         html = sel.select("./td")[1].html()
    #         # print(dayweek, number, html)
    #         schedule[dayweek] = schedule.get(dayweek, {})
    #         schedule[dayweek][number] = html
    #     if sel.select("./td").count() == 3:
    #         dayweek = WEEKDAYS[sel.select("./td")[0].text()]
    #         number = sel.select("./td")[1].text()
    #         html = sel.select("./td")[2].html()
    #         # print(dayweek, number, html)
    #         schedule[dayweek] = schedule.get(dayweek, {})
    #         schedule[dayweek][number] = html
    #     # print(sel.select("./td").count())
    # print(json.dumps(schedule, ensure_ascii=False))

    # html = schedule[1]["4"]
    # print(html)
    # sel = Selector(fromstring(html))

    # print(parseSubjectTable(sel))

    # print(sel.select("//table//tr").count())
    # print(sel.select("//table//td").count())
