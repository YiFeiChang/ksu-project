import re
from urllib.parse import unquote

def extract_matches_to_file(text: str, regex_pattern: str, output_filepath: str = 'output.txt') -> None:
    # 擷取所有符合正規表達式的內容
    matches: list[str] = re.findall(regex_pattern, text)
    
    # 將結果寫入指定的輸出檔案中
    with open(output_filepath, 'w', encoding='utf-8') as file:
        for match in matches:
            decoded_url = unquote(match)
            file.write(f"\"{decoded_url}\",\n")

text: str = """
/*O_o*/
google.search.cse.api13879({
  "cursor": {
    "currentPageIndex": 2,
    "estimatedResultCount": "39600",
    "moreResultsUrl": "http://www.google.com/cse?oe=utf8&ie=utf8&source=uds&q=%E8%8D%89%E8%8E%93%E7%A8%AE%E6%A4%8D&safe=off&start=20&sort=&cx=010390367945092689201:i9mcekrypva",
    "resultCount": "39,600",
    "searchResultTime": "0.39",
    "pages": [
      {
        "label": 1,
        "start": "0"
      },
      {
        "label": 2,
        "start": "10"
      },
      {
        "label": 3,
        "start": "20"
      },
      {
        "label": 4,
        "start": "30"
      },
      {
        "label": 5,
        "start": "40"
      },
      {
        "label": 6,
        "start": "50"
      },
      {
        "label": 7,
        "start": "60"
      },
      {
        "label": 8,
        "start": "70"
      },
      {
        "label": 9,
        "start": "80"
      },
      {
        "label": 10,
        "start": "90"
      }
    ]
  },
  "results": [
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/subject/subject.php%3Fid%3D12668&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQIBBAB&usg=AOvVaw1Ahqx77L3b6qO_1HVkD6rA",
      "content": "民國46年，大湖鄉民賴雲添到親戚李安章家看到這種新興作物引起栽培的興趣，次年就夥同陳世源、吳世金等農友購進種苗，栽培0.4公頃，此為大湖草苺栽種的開端。 草苺的\u003cb\u003e種植\u003c/b\u003e是以&nbsp;...",
      "contentNoFormatting": "民國46年，大湖鄉民賴雲添到親戚李安章家看到這種新興作物引起栽培的興趣，次年就夥同陳世源、吳世金等農友購進種苗，栽培0.4公頃，此為大湖草苺栽種的開端。 草苺的種植是以 ...",
      "title": "草苺起源-\u003cb\u003e草莓\u003c/b\u003e主題館 - 農業知識入口網",
      "titleNoFormatting": "草苺起源-草莓主題館 - 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=12668",
      "unescapedUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=12668",
      "url": "https://kmweb.moa.gov.tw/subject/subject.php%3Fid%3D12668",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {
        "cseImage": {
          "src": "https://kmwebsys.moa.gov.tw/files/subject_WS/12668/A02_1.jpg"
        },
        "metatags": {
          "viewport": "width=device-width, initial-scale=1.0, maximum-scale=1.0, minimal-ui,  user-scalable=no",
          "ogTitle": "農業知識入口網-草苺起源",
          "ogUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=12668",
          "ogDescription": "我們日常吃到的農產品，有許多是在台灣光復之後才引進新品種試種與試殖成功的。這些新產品，當年引進試種、試殖，都有一段艱辛歷程。前人種樹，後人遮蔭；本報特自今天起作...",
          "ogImage": "https://kmweb.moa.gov.twhttps://kmwebsys.moa.gov.tw/files/subject_WS/12668/A02_1.jpg",
          "ogImageSecureUrl": "https://kmweb.moa.gov.twhttps://kmwebsys.moa.gov.tw/files/subject_WS/12668/A02_1.jpg",
          "fbAppId": "1445554895733029",
          "ogType": "website"
        }
      },
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "subject",
          "subject"
        ]
      }
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/subject/subject.php%3Fid%3D1343%26page%3D3%26display_num%3D20&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQICRAB&usg=AOvVaw0DWwss155DGpFmp-bEqsbB",
      "content": "跳到主要內容. 農業知識入口網. ::: \u003cb\u003e草莓\u003c/b\u003e介紹 &middot; \u003cb\u003e草莓\u003c/b\u003e品種; \u003cb\u003e草莓\u003c/b\u003e觀光採果. 觀光休閒簡介 &middot; 採果導覽 &middot; 草苺酒庄 &middot; 草苺文化館 &middot; 有機\u003cb\u003e草莓\u003c/b\u003e; \u003cb\u003e草莓\u003c/b\u003e栽培及生理.",
      "contentNoFormatting": "跳到主要內容. 農業知識入口網. ::: 草莓介紹 · 草莓品種; 草莓觀光採果. 觀光休閒簡介 · 採果導覽 · 草苺酒庄 · 草苺文化館 · 有機草莓; 草莓栽培及生理.",
      "title": "\u003cb\u003e草莓\u003c/b\u003eQ&amp;A - 農業知識入口網",
      "titleNoFormatting": "草莓Q&A - 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=1343&amp;page=3...",
      "unescapedUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=1343&page=3&display_num=20",
      "url": "https://kmweb.moa.gov.tw/subject/subject.php%3Fid%3D1343%26page%3D3%26display_num%3D20",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {
        "cseImage": {
          "src": "https://kmweb.moa.gov.tw/images/default_2.jpg"
        },
        "metatags": {
          "viewport": "width=device-width, initial-scale=1.0, maximum-scale=1.0, minimal-ui,  user-scalable=no",
          "ogTitle": "農業知識入口網-草莓Q&A",
          "ogUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=1343&page=3&display_num=20",
          "ogImage": "https://kmweb.moa.gov.tw/images/default_2.jpg",
          "ogImageSecureUrl": "https://kmweb.moa.gov.tw/images/default_2.jpg",
          "fbAppId": "1445554895733029",
          "ogType": "website"
        }
      },
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "subject",
          "subject"
        ]
      }
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D3073&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQIDBAB&usg=AOvVaw0yuVWh0SaV2tW5WNCMQ95u",
      "content": "為什麼還是沒有發芽?原因是用草苺種子栽種\u003cb\u003e草莓\u003c/b\u003e，成功機率是非常之低。所以ㄧ般栽種\u003cb\u003e草莓\u003c/b\u003e是利用「走莖」來繁殖。 當白晝日漸增長，氣溫逐漸升高、也就是三、四月分時，\u003cb\u003e草莓\u003c/b\u003e原來的&nbsp;...",
      "contentNoFormatting": "為什麼還是沒有發芽?原因是用草苺種子栽種草莓，成功機率是非常之低。所以ㄧ般栽種草莓是利用「走莖」來繁殖。 當白晝日漸增長，氣溫逐漸升高、也就是三、四月分時，草莓原來的 ...",
      "title": "\u003cb\u003e草莓\u003c/b\u003e種子\u003cb\u003e種植\u003c/b\u003e - 農業知識入口網",
      "titleNoFormatting": "草莓種子種植 - 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=3073",
      "unescapedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=3073",
      "url": "https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D3073",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {
        "cseImage": {
          "src": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg"
        },
        "metatags": {
          "twitterTitle": "草莓種子種植 - 農業知識入口網",
          "ogImageWidth": "900",
          "twitterImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogTitle": "草莓種子種植 - 農業知識入口網",
          "ogDescription": "這次參加種植的部落格比賽..有嘗試種植草莓..有放基肥..每天澆水..為什麼還是沒有發芽?..",
          "ogImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogImageType": "image/jpeg",
          "ogType": "website",
          "twitterCard": "summary_large_image",
          "viewport": "width=device-width, initial-scale=1.0, maximum-scale=1.0, minimal-ui, user-scalable=no",
          "formatDetection": "telephone=no",
          "ogImageHeight": "400",
          "twitterDescription": "這次參加種植的部落格比賽..有嘗試種植草莓..有放基肥..每天澆水..為什麼還是沒有發芽?..",
          "ogUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=3073",
          "ogImageSecureUrl": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "fbAppId": "1445554895733029"
        }
      },
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "knowledge_view"
        ]
      }
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D868&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQIBRAB&usg=AOvVaw0R-YqsImIVK-t4vyZ_EKmT",
      "content": "高架床栽培\u003cb\u003e草莓\u003c/b\u003e是一項創新技術，對栽培者或消費者而言，皆是一種福音。其離地易於管理之栽培方法，亦適合老年人當做休閒園藝活動；高架床可因地方大小調整長短，無論城市或鄉村，&nbsp;...",
      "contentNoFormatting": "高架床栽培草莓是一項創新技術，對栽培者或消費者而言，皆是一種福音。其離地易於管理之栽培方法，亦適合老年人當做休閒園藝活動；高架床可因地方大小調整長短，無論城市或鄉村， ...",
      "title": "高架栽培的\u003cb\u003e草莓\u003c/b\u003e，與傳統栽培有何不同? - 農業知識入口網",
      "titleNoFormatting": "高架栽培的草莓，與傳統栽培有何不同? - 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=868",
      "unescapedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=868",
      "url": "https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D868",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {
        "cseImage": {
          "src": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg"
        },
        "metatags": {
          "twitterTitle": "高架栽培的草莓，與傳統栽培有何不同? - 農業知識入口網",
          "ogImageWidth": "900",
          "twitterImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogTitle": "高架栽培的草莓，與傳統栽培有何不同? - 農業知識入口網",
          "ogDescription": "一般的草莓園，草莓都是長得接近地面上。據說有種高架栽培法，那種方法與傳統作法那裡不一樣樣，又有什麼好處？是不是就是有機的？那裡可以買到?",
          "ogImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogImageType": "image/jpeg",
          "ogType": "website",
          "twitterCard": "summary_large_image",
          "viewport": "width=device-width, initial-scale=1.0, maximum-scale=1.0, minimal-ui, user-scalable=no",
          "formatDetection": "telephone=no",
          "ogImageHeight": "400",
          "twitterDescription": "一般的草莓園，草莓都是長得接近地面上。據說有種高架栽培法，那種方法與傳統作法那裡不一樣樣，又有什麼好處？是不是就是有機的？那裡可以買到?",
          "ogUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=868",
          "ogImageSecureUrl": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "fbAppId": "1445554895733029"
        }
      },
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "knowledge_view"
        ]
      }
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D1728&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQIAxAB&usg=AOvVaw3MkdPo_aPoxsmzieV4Rafe",
      "content": "☆節氣小農夫有句俗諺「小滿梅雨在本島，\u003cb\u003e種植\u003c/b\u003e花木皆成寶」，這句話的意思是：小滿節氣適逢梅雨季，如果在這個時候\u003cb\u003e種植\u003c/b\u003e花草樹木等植物或進行扦插、稼接等工作，植物的成長速度會&nbsp;...",
      "contentNoFormatting": "☆節氣小農夫有句俗諺「小滿梅雨在本島，種植花木皆成寶」，這句話的意思是：小滿節氣適逢梅雨季，如果在這個時候種植花草樹木等植物或進行扦插、稼接等工作，植物的成長速度會 ...",
      "title": "請問現在可以\u003cb\u003e種植草莓\u003c/b\u003e嗎？ - 農業知識入口網",
      "titleNoFormatting": "請問現在可以種植草莓嗎？ - 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=1728",
      "unescapedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=1728",
      "url": "https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D1728",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {
        "cseImage": {
          "src": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg"
        },
        "metatags": {
          "twitterTitle": "請問現在可以種植草莓嗎？ - 農業知識入口網",
          "ogImageWidth": "900",
          "twitterImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogTitle": "請問現在可以種植草莓嗎？ - 農業知識入口網",
          "ogDescription": "好想吃自己種的草莓阿。不知道現在7月可以開始種了嗎？",
          "ogImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogImageType": "image/jpeg",
          "ogType": "website",
          "twitterCard": "summary_large_image",
          "viewport": "width=device-width, initial-scale=1.0, maximum-scale=1.0, minimal-ui, user-scalable=no",
          "formatDetection": "telephone=no",
          "ogImageHeight": "400",
          "twitterDescription": "好想吃自己種的草莓阿。不知道現在7月可以開始種了嗎？",
          "ogUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=1728",
          "ogImageSecureUrl": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "fbAppId": "1445554895733029"
        }
      },
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "knowledge_view"
        ]
      }
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/knowledgebase.php%3Ffunc%3D2%26type%3D12894%26id%3D414925&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQIChAB&usg=AOvVaw0sgGAWUMbXCV6xvP3y5wH4",
      "content": "\u003cb\u003e草莓\u003c/b\u003e為薔薇科\u003cb\u003e草莓\u003c/b\u003e屬多年生草本植物， 國內栽培種屬八倍體，根據農業統計年報， 台灣於109 年\u003cb\u003e草莓\u003c/b\u003e栽培面積達到527 公頃， 年產量達9,873 公噸，年產值約13 億。",
      "contentNoFormatting": "草莓為薔薇科草莓屬多年生草本植物， 國內栽培種屬八倍體，根據農業統計年報， 台灣於109 年草莓栽培面積達到527 公頃， 年產量達9,873 公噸，年產值約13 億。",
      "title": "苗栗區農業專訊第96期－\u003cb\u003e草莓\u003c/b\u003e品種特性對栽培之影響- 農業知識入口網",
      "titleNoFormatting": "苗栗區農業專訊第96期－草莓品種特性對栽培之影響- 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/knowledgebase.php?func=2&amp;type=12894...",
      "unescapedUrl": "https://kmweb.moa.gov.tw/knowledgebase.php?func=2&type=12894&id=414925",
      "url": "https://kmweb.moa.gov.tw/knowledgebase.php%3Ffunc%3D2%26type%3D12894%26id%3D414925",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {},
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "knowledgebase"
        ]
      }
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D2766&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQIBxAB&usg=AOvVaw0c2GYWYG2abV8JrwXU6MtS",
      "content": "... \u003cb\u003e種植\u003c/b\u003e；或是讓走莖上的小苗隨意生長，栽種時再從泥土中鏟出，不過這樣小苗的根部比較容易受傷。栽種\u003cb\u003e草莓\u003c/b\u003e苗的工作叫做「定植」，\u003cb\u003e草莓\u003c/b\u003e的定植不像稻子插秧可以利用機器耕作&nbsp;...",
      "contentNoFormatting": "... 種植；或是讓走莖上的小苗隨意生長，栽種時再從泥土中鏟出，不過這樣小苗的根部比較容易受傷。栽種草莓苗的工作叫做「定植」，草莓的定植不像稻子插秧可以利用機器耕作 ...",
      "title": "\u003cb\u003e草莓\u003c/b\u003e的施肥 - 農業知識入口網",
      "titleNoFormatting": "草莓的施肥 - 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=2766",
      "unescapedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=2766",
      "url": "https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D2766",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {
        "cseImage": {
          "src": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg"
        },
        "metatags": {
          "twitterTitle": "草莓的施肥 - 農業知識入口網",
          "ogImageWidth": "900",
          "twitterImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogTitle": "草莓的施肥 - 農業知識入口網",
          "ogDescription": "我種的草莓開很多花，可是結的果實卻非常的小。1.請問是施肥出問題嗎？2.草莓適合哪一種肥料？",
          "ogImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogImageType": "image/jpeg",
          "ogType": "website",
          "twitterCard": "summary_large_image",
          "viewport": "width=device-width, initial-scale=1.0, maximum-scale=1.0, minimal-ui, user-scalable=no",
          "formatDetection": "telephone=no",
          "ogImageHeight": "400",
          "twitterDescription": "我種的草莓開很多花，可是結的果實卻非常的小。1.請問是施肥出問題嗎？2.草莓適合哪一種肥料？",
          "ogUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=2766",
          "ogImageSecureUrl": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "fbAppId": "1445554895733029"
        }
      },
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "knowledge_view"
        ]
      }
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/subject/subject.php%3Fid%3D55354&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQICBAC&usg=AOvVaw1oMwXLNBeIO0zXjFS9Szs9",
      "content": "2024年1月17日 \u003cb\u003e...\u003c/b\u003e ☆節氣小農夫有句俗諺「小滿梅雨在本島，\u003cb\u003e種植\u003c/b\u003e花木皆成寶」，這句話的意思是：小滿節氣適逢梅雨季，如果在這個時候\u003cb\u003e種植\u003c/b\u003e花草樹木等植物或進行扦插、稼接&nbsp;...",
      "contentNoFormatting": "2024年1月17日 ... ☆節氣小農夫有句俗諺「小滿梅雨在本島，種植花木皆成寶」，這句話的意思是：小滿節氣適逢梅雨季，如果在這個時候種植花草樹木等植物或進行扦插、稼接 ...",
      "title": "\u003cb\u003e草莓\u003c/b\u003e（白\u003cb\u003e草莓\u003c/b\u003e） - 農業知識入口網",
      "titleNoFormatting": "草莓（白草莓） - 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=55354",
      "unescapedUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=55354",
      "url": "https://kmweb.moa.gov.tw/subject/subject.php%3Fid%3D55354",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {
        "cseImage": {
          "src": "https://kmweb.moa.gov.tw/files/knowledge_question/16290/A01_1_m.jpeg"
        },
        "metatags": {
          "twitterTitle": "草莓（白草莓） - 農業知識入口網",
          "ogImageWidth": "810",
          "twitterImage": "https://kmweb.moa.gov.tw/files/knowledge_question/16290/A01_1_m.jpeg",
          "ogTitle": "草莓（白草莓） - 農業知識入口網",
          "ogDescription": "請問我第一次種白草莓：白草莓如何看成熟度？大小棵差很多如何讓草莓長大成度差不多大？同一批有得到現在還沒結果實？我有追肥有機肥料草莓ㄧ株結很多果實要疏果實嗎？還是追肥即可走莖出來的草莓苗果實量會比母株來...",
          "ogImage": "https://kmweb.moa.gov.tw/files/knowledge_question/16290/A01_1_m.jpeg",
          "ogImageType": "image/jpeg",
          "ogType": "website",
          "twitterCard": "summary_large_image",
          "viewport": "width=device-width, initial-scale=1.0, maximum-scale=1.0, minimal-ui, user-scalable=no",
          "formatDetection": "telephone=no",
          "ogImageHeight": "1080",
          "twitterDescription": "請問我第一次種白草莓：白草莓如何看成熟度？大小棵差很多如何讓草莓長大成度差不多大？同一批有得到現在還沒結果實？我有追肥有機肥料草莓ㄧ株結很多果實要疏果實嗎？還是追肥即可走莖出來的草莓苗果實量會比母株來...",
          "ogUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=16290",
          "ogImageSecureUrl": "https://kmweb.moa.gov.tw/files/knowledge_question/16290/A01_1_m.jpeg",
          "fbAppId": "1445554895733029"
        }
      },
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "subject",
          "subject"
        ]
      }
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/subject/subject.php%3Fid%3D59344&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQICxAB&usg=AOvVaw1bq_-n4IPrRkCRozyzp22x",
      "content": "我一週前買2.5吋白\u003cb\u003e草莓\u003c/b\u003e苗，三天前移植到大概六吋的盆栽裡面，目前因為陰雨天只有換盆時有給過一次水。 \u003cb\u003e種植\u003c/b\u003e環境/地點：陽台；光照時間：全日照；給水頻率：1次/2-3天；給水方式：淹&nbsp;...",
      "contentNoFormatting": "我一週前買2.5吋白草莓苗，三天前移植到大概六吋的盆栽裡面，目前因為陰雨天只有換盆時有給過一次水。 種植環境/地點：陽台；光照時間：全日照；給水頻率：1次/2-3天；給水方式：淹 ...",
      "title": "白\u003cb\u003e草莓\u003c/b\u003e的花葉變黑 - 農業知識入口網",
      "titleNoFormatting": "白草莓的花葉變黑 - 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=59344",
      "unescapedUrl": "https://kmweb.moa.gov.tw/subject/subject.php?id=59344",
      "url": "https://kmweb.moa.gov.tw/subject/subject.php%3Fid%3D59344",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {
        "cseImage": {
          "src": "https://kmweb.moa.gov.tw/files/knowledge_question/18601/A01_1_m.jpg"
        },
        "metatags": {
          "twitterTitle": "白草莓的花葉變黑 - 農業知識入口網",
          "ogImageWidth": "810",
          "twitterImage": "https://kmweb.moa.gov.tw/files/knowledge_question/18601/A01_1_m.jpg",
          "ogTitle": "白草莓的花葉變黑 - 農業知識入口網",
          "ogDescription": "我是第一次養白草莓，請問白草莓花葉的部分開始變黑是什麼原因呢？我一週前買2.5吋白草莓苗，三天前移植到大概六吋的盆栽裡面，目前因為陰雨天只有換盆時有給過一次水。",
          "ogImage": "https://kmweb.moa.gov.tw/files/knowledge_question/18601/A01_1_m.jpg",
          "ogImageType": "image/jpeg",
          "ogType": "website",
          "twitterCard": "summary_large_image",
          "viewport": "width=device-width, initial-scale=1.0, maximum-scale=1.0, minimal-ui, user-scalable=no",
          "formatDetection": "telephone=no",
          "ogImageHeight": "1080",
          "twitterDescription": "我是第一次養白草莓，請問白草莓花葉的部分開始變黑是什麼原因呢？我一週前買2.5吋白草莓苗，三天前移植到大概六吋的盆栽裡面，目前因為陰雨天只有換盆時有給過一次水。",
          "ogUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=18601",
          "ogImageSecureUrl": "https://kmweb.moa.gov.tw/files/knowledge_question/18601/A01_1_m.jpg",
          "fbAppId": "1445554895733029"
        }
      },
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "subject",
          "subject"
        ]
      }
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=010390367945092689201:i9mcekrypva&q=https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D6949&sa=U&ved=2ahUKEwjI3_K7stGUAxUoa_UHHVurIfs4FBAWegQIBhAB&usg=AOvVaw0ip4z5wASem2PsLKx_z1RV",
      "content": "☆節氣小農夫有句俗諺「小滿梅雨在本島，\u003cb\u003e種植\u003c/b\u003e花木皆成寶」，這句話的意思是：小滿節氣適逢梅雨季，如果在這個時候\u003cb\u003e種植\u003c/b\u003e花草樹木等植物或進行扦插、稼接等工作，植物的成長速度會&nbsp;...",
      "contentNoFormatting": "☆節氣小農夫有句俗諺「小滿梅雨在本島，種植花木皆成寶」，這句話的意思是：小滿節氣適逢梅雨季，如果在這個時候種植花草樹木等植物或進行扦插、稼接等工作，植物的成長速度會 ...",
      "title": "\u003cb\u003e草莓\u003c/b\u003e只長葉不開花 - 農業知識入口網",
      "titleNoFormatting": "草莓只長葉不開花 - 農業知識入口網",
      "formattedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=6949",
      "unescapedUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=6949",
      "url": "https://kmweb.moa.gov.tw/knowledge_view.php%3Fid%3D6949",
      "visibleUrl": "kmweb.moa.gov.tw",
      "richSnippet": {
        "cseImage": {
          "src": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg"
        },
        "metatags": {
          "twitterTitle": "草莓只長葉不開花 - 農業知識入口網",
          "ogImageWidth": "900",
          "twitterImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogTitle": "草莓只長葉不開花 - 農業知識入口網",
          "ogDescription": "跟朋友同期種的草莓苗，朋友的卻開花了，我的卻只有一直長葉卻不開花是什麼關係造成的呢?謝謝",
          "ogImage": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "ogImageType": "image/jpeg",
          "ogType": "website",
          "twitterCard": "summary_large_image",
          "viewport": "width=device-width, initial-scale=1.0, maximum-scale=1.0, minimal-ui, user-scalable=no",
          "formatDetection": "telephone=no",
          "ogImageHeight": "400",
          "twitterDescription": "跟朋友同期種的草莓苗，朋友的卻開花了，我的卻只有一直長葉卻不開花是什麼關係造成的呢?謝謝",
          "ogUrl": "https://kmweb.moa.gov.tw/knowledge_view.php?id=6949",
          "ogImageSecureUrl": "https://kmweb.moa.gov.tw/files/banner/2/A01-s_1.jpg",
          "fbAppId": "1445554895733029"
        }
      },
      "breadcrumbUrl": {
        "host": "kmweb.moa.gov.tw",
        "crumbs": [
          "knowledge_view"
        ]
      }
    }
  ],
  "findMoreOnGoogle": {
    "url": "https://www.google.com/search?client=ms-google-coop&q=%E8%8D%89%E8%8E%93%E7%A8%AE%E6%A4%8D&cx=010390367945092689201:i9mcekrypva"
  }
});
"""
if __name__ == '__main__':
    pattern: str = r'(?<="url":\s")https://kmweb.moa.gov.tw/.*?(?=")'
    extract_matches_to_file(text, pattern)