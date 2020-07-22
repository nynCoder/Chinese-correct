"""
简单中文文本纠错之根据用户输入query进行纠错。基于用户词表，拼音相似度与编辑距离的查询纠错。
这里我们的大致思路：
1.分词
2.利用中文单字表等，对每个词进行插入删除替换等操作生成一系列候选词，并通过准备好的词典对候选词进行过滤
3.对候选词召回：这里是按拼音，和query中的词拼音完全一样，作为一级候选者，首字母拼音一样，作为二级，其他作为三级，并从中选出
在字典中词频最大那个作为正确的来纠正替换query中的错误词汇【考虑到按照拼音也会产生很多候选，这里对拼音得到的候选词可以进行加权作为打分，两个算法的分数结合方面，虽然两个算法有些相似但仍有不同点，
我们更倾向于选择最长公共子串分数更高的，但是同样得考虑编辑距离，在经过观察与实验后选定最终分数为 0.5*编辑距离 + 0.8*LCS。这样，两个字符串在匹配的时候，既能以公共子串为主，又能考虑到少部分拼音出错的因素。取topk
返回作为，同时​ 对于最长公共子串，最终的结果是两个字符串最长公共子串的长度，越大则两个字符串匹配程度越高。考虑到越长的字符串最后的公共子串更可能越长，
这对短字符串不公平，因此我将最终的最长子串长度除以第一个字符串（错误词语的拼音）的长度进行归一化。】。
4将正确的词汇重新拼为完整句子
"""
import os,sys
import pinyin,re
import jieba
import string
#带声调的拼音
PINYIN = {'ā': ['a', 1], 'á': ['a', 2], 'ǎ': ['a', 3], 'à': ['a', 4],
          'ē': ['e', 1], 'é': ['e', 2], 'ě': ['e', 3], 'è': ['e', 4],
          'ī': ['i', 1], 'í': ['i', 2], 'ǐ': ['i', 3], 'ì': ['i', 4],
          'ō': ['o', 1], 'ó': ['o', 2], 'ǒ': ['o', 3], 'ò': ['o', 4],
          'ū': ['u', 1], 'ú': ['u', 2], 'ǔ': ['u', 3], 'ù': ['u', 4],
          'ǖ': ['ü', 1], 'ǘ': ['ü', 2], 'ǚ': ['ü', 3], 'ǜ': ['ü', 4],
          '': ['m', 2], 'ń': ['n', 2], 'ň': ['n', 3], 'ǹ': ['n', 4],
          }
FILE_PATH = "token_freq_pos%40350k_jieba.txt"
#所有的标点字符,'!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
PUNCTUATION_LIST = string.punctuation
PUNCTUATION_LIST += "。，？：；｛｝［］‘“”《》／！％……（）"#添加一些
def construct_dict(file):
    word_freq={}
    with open(file,"r",encoding="utf-8")as rf:
        for line in rf:
            info=line.split()
            #word=info[0],freq=info[1]
            word_freq[info[0]]=info[1]
    return word_freq
def load_cn_words_dict(file):
    cn_words_dict=""
    with open(file,"r",encoding="utf-8")as rf:
        for word in rf:
            cn_words_dict+=word.strip()
    return cn_words_dict
def  edits(phrase,cn_words_dict):
    #增加、删除、替换等操作生成可能的候选词，这是编辑距离为1的
#     phrase=phrase.decode("utf-8")
    splits=[(phrase[:i],phrase[i:]) for i in range(len(phrase)+1)]
    deletes    = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
    replaces   = [L + c + R[1:] for L, R in splits if R for c in cn_words_dict]
    inserts    = [L + c + R for L, R in splits for c in cn_words_dict]
    return set(deletes + transposes + replaces + inserts)
def known(phrases):
    #只要历史中出现过的词汇
    return set(phrase for phrase in phrases if phrase in phrase_freq)
def get_candidates(query):
    candi_1st_order=[]
    candi_2nd_order=[]
    candi_3nd_order=[]
    query_pinyin=pinyin.get(query,format="strip",delimiter="/")
    cn_words_dict=load_cn_words_dict("cn_dict.txt")
    candidates=list(known(edits(query,cn_words_dict)))
    for can in candidates:
        candi_pinyin=pinyin.get(can,format="strip",delimiter="/")
        if candi_pinyin==query_pinyin:
            candi_1st_order.append(can)
        elif candi_pinyin.split("/")[0]==query_pinyin.split("/")[0]:
            candi_2nd_order.append(can)
        else:
            candi_3nd_order.append(can)
    return candi_1st_order,candi_2nd_order,candi_3nd_order
def auto_correct(query):
    c1_order,c2_order,c3_order=get_candidates(query)
    if c1_order:
        #返回词频最大的那个
        return max(c1_order,key=phrase_freq.get)
    elif c2_order:
        return max(c2_order,key=phrase_freq.get)
    else:
        return max(c3_order,key=phrase_freq.get)
def auto_correct_sentence(query_sentence,verbose=True):
    jieba_cut = jieba.cut(query_sentence, cut_all=False)
    seg_list = "\t".join(jieba_cut).split("\t")
    correct_sentence=""
    for phrase in seg_list:
        correct_phrase=phrase
        # check if item is a punctuation
        if phrase not in PUNCTUATION_LIST:
            # check if the phrase in our dict, if not then it is a misspelled phrase
            if phrase not in phrase_freq.keys():
                correct_phrase=auto_correct(phrase)
                if verbose:
                    print(phrase,correct_phrase)
        correct_sentence+=correct_phrase
    return correct_sentence
err_sent_1 = '人工智能领遇最能体现智能的一个分知是机七学习！'
phrase_freq = construct_dict(FILE_PATH)
correct_sent=auto_correct_sentence(err_sent_1)
print("original sentence:" + err_sent_1 + "\n==>\n" + "corrected sentence:" + correct_sent)