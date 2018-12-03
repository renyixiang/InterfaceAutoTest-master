#coding:utf-8
import json
import logging
import re
import  time
from _mysql import IntegrityError

from jsonpath_rw import jsonpath, parse

import requests
from django.contrib.gis import serializers
from django.core.paginator import Paginator
from django.shortcuts import render,redirect
from InterfaceTestManage.models import userInfo, project, Environment, TestCase
from django.http import HttpResponseRedirect,JsonResponse,HttpResponse
from django.utils.datastructures import MultiValueDictKeyError
from django.core   import serializers

from InterfaceTestManage.utils import loghelper

loghelper = loghelper.loghelper()
logger = loghelper.get_logger()

# Create your views here.
def login_check(func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('username'):
            return HttpResponseRedirect('/login')
        return func(request, *args, **kwargs)
        #func(request, *args, **kwargs)
    return wrapper



'''获取首页'''
@login_check
def getIndex(request):

    username = request.session.get('username','')
    context = {'title': '欢迎进入接口测试页','username':username}
    return  render(request,'index.html',context)

'''统计页面'''
@login_check
def welcome(request):
    context={'title':'主页统计页面'}
    return  render(request,'welcome.html',context)

'''登录'''
def login(request):
    if request.method == 'GET':
        #如果用户第一次点击了记住密码，先从Cookie里面取值，在填充。
        username=request.COOKIES.get('username','') #后面的空值是默认值，如果不填默认为None
        password = request.COOKIES.get('password','')
        context = {'title':'API接口自动化测试系统登录','username':username,'password':password}
        return  render(request,'login.html',context)
    else:
        #post发送请求，就是表单里面的请求进来了
        username = request.POST['username']
        password = request.POST['password']

        user = userInfo.objects
        user_info = user.filter(username=username,password=password)
        count = user_info.count()
        if  count:
            #登录成功，如果存在用户名和密码
            #remeberPw = request.POST['remeberPw']
            request.session['username'] = username
            remeberPw = request.POST.get('remeberPw')
            redirect_index = HttpResponseRedirect('/index')
            if  remeberPw:
                print("用户记住了密码啊！！")
                redirect_index.set_cookie('username',username)
                redirect_index.set_cookie('password',password)

            logger.info('{username} 登录成功'.format(username=username))
            loghelper.close_handler()
            return redirect_index
            #return  request.getRequestDispatcher().forward('/index')

        else:
            print('用户名或密码错误')
            context = {'message':'用户名或密码错误'}
            logger.info('用户名:{username}和密码:{password}存在错误啊！ '.format(username=username,password=password))
            loghelper.close_handler()
            return JsonResponse(context)



'''注册'''
def register(request):
    if request.method == 'GET':
        content={'title':'注册账号'}
        return render(request,'user-add.html',content)
    else:
        reqParams = eval(request.body)
        username=reqParams.get('username','')
        phone=reqParams.get('phone','')
        email=reqParams.get('email','')
        password=reqParams.get('password','')

        # username= request.POST['username']
        # phone = request.POST['phone']
        # email = request.POST['email']
        # #TODO 角色这块后面再做
        # password = request.POST['password']

        user_info = userInfo.objects
        #将数据进行注册
        #后台对获取的数据进行校验,之后在传递.
        if(username is not None and len(username) <=8 and password is not None
            and  len(password)<=16 ):
            try:
                user_info.create(username=username,password=password,phone=phone)
                #return HttpResponseRedirect('/login')
                context = {"success":"注册成功"}
                return JsonResponse(context)
            except MultiValueDictKeyError as error:
                #如果想html页面通知发生错误了？比如500之内的。。
                print("用户名重复了啊")
                context = {"success": "注册出现异常了，请查看日志哦"+str(error)}
                return JsonResponse(context)
            except IntegrityError as error:
                print(str(error))
                context = {"success": "用户名重复了啊!" }
                return JsonResponse(context)

            # user_info.create(username=username,password=password,phone=phone)
            # return HttpResponseRedirect('/login')
        else:
            context = {"success": "注册出现其他问题"}
            return JsonResponse(context);

'''项目管理'''
@login_check
def projectManager(request,id):
    if request.method == 'GET':
        projects = project.objects
        projectList = projects.all().order_by('id')
        paginator = Paginator(projectList, 8)
        firstPage =id
        #默认id的值传递为0
        if int(firstPage) > 0:
            pages = paginator.page(int(firstPage))
        else:
            firstPage =1
            pages = paginator.page(1)
        projectList =pages.object_list
        #print("-------------"+pages.has_next())
        context = {'projectList':projectList,'pageList':paginator,'currentPag':int(firstPage),"pages":pages}
        print(projectList)
        return  render(request,'project-list.html',context)

'''项目新增'''
@login_check
def projectAdd(request):
    if request.method == 'GET':
        context={'title':'增加项目','btn':'增加'}
        return  render(request,'project-add.html',context)
    if request.method == 'POST':
        projectName = request.POST.get('projectName','')
        projectdesc = request.POST.get('projectdesc','')
        username = request.session.get("username",'')
        project_info = project.objects
        if projectName:
            project_info.create(projectName=projectName,projectdesc=projectdesc,username=username)
            #return HttpResponseRedirect('/api/projectManager/0')
            #context = ''
            context={'success':'添加成功啦'}
            return  JsonResponse(context)
            #return HttpResponseRedirect('/api/projectManager/0')
        else:
            context = '添加失败了，请重新添加'
            return JsonResponse({'error':context})


@login_check
def projectEdit(request,id):
    if request.method == 'GET':
        project_obj = project.objects
        project_info = project_obj.get(id=id)
        context = {'projectName':project_info.projectName,'projectdesc':project_info.projectdesc,'btn':'编辑','id':id}
        return render(request,'project-add.html',context)
    elif request.is_ajax():
        projectName = request.POST.get('projectName')
        projectdesc = request.POST.get('projectdesc')
        if int(id):
            project_obj = project.objects
            project_info = project_obj.filter(id=id)
            update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            try:
                project_info.update(projectName=projectName,projectdesc=projectdesc,update_time=update_time)
                context = {'success': '编辑项目成功咯'}
            except:
                context = {'success':'编辑失败了'}
        return JsonResponse(context)

@login_check
def projectDelete(request,id):
    if request.method == "GET":
        if len(id) > 0:
            project.objects.filter(id=id).delete()
            context={"success":"删除成功！"}
            return  JsonResponse(context)
    elif request.is_ajax():
        ##删除所有
        ids = request.POST.get("ids")
        ids = eval(ids)
        if type(ids) != int:
            for id in ids:
                project.objects.filter(id=id).delete()
            context = {"success": "删除成功！"}
        else:
            project.objects.filter(id=ids).delete()
            context = {"success": "删除成功！"}
        return JsonResponse(context)


@login_check
def logout(request):
    #request.session['username'] = None
    if request.method == 'GET':
        try:
            del request.session['username']
        except KeyError:
            print(KeyError)
    return  HttpResponseRedirect('/login')

'''环境管理'''
@login_check
def EnviromentManager(request,id):
    if request.method == 'GET':
        environ = Environment.objects
        environList = environ.all().order_by('id')
        paginator = Paginator(environList, 8)
        firstPage =id
        #默认id的值传递为0
        if int(firstPage) > 0:
            pages = paginator.page(int(firstPage))
        else:
            firstPage =1
            pages = paginator.page(1)
        environList =pages.object_list
        context = {'environList':environList,'pageList':paginator,'currentPag':int(firstPage),"pages":pages,"title":"测试环境管理"}
        return  render(request,'environ-list.html',context)


'''项目新增'''
@login_check
def environmentAdd(request):
    if request.method == 'GET':
        context={'title':'环境添加','btn':'增加'}
        return  render(request,'environ-add.html',context)
    if request.method == 'POST':
        path_name = request.POST.get('path_name','')
        host = request.POST.get('host','')
        port = request.POST.get('port', '')
        envir_descript = request.POST.get('envir_descript', '')
        username = request.session.get("username",'')
        environment = Environment.objects
        if len(path_name) >0:
            environment.create(path_name=path_name,host=host,port=port,envir_descript=envir_descript,username=username)
            context={'success':'添加成功啦'}
            return  JsonResponse(context)
            #return HttpResponseRedirect('/api/projectManager/0')
        else:
            context = '添加失败了，请重新添加'
            return JsonResponse({'error':context})

@login_check
def environmentEdit(request,id):
    if request.method == 'GET':
        environ_obj = Environment.objects
        environ_info = environ_obj.get(id=id)
        #context = {'path_name':project_info.path_name,'envir_descript':environ_info.envir_descript,'btn':'编辑','id':id}
        context = {'environ_info': environ_info, 'btn': '编辑','id': id}
        return render(request,'environ-add.html',context)
    elif request.is_ajax():
        path_name = request.POST.get('path_name', '')
        host = request.POST.get('host', '')
        port = request.POST.get('port', '')
        envir_descript = request.POST.get('envir_descript', '')

        if int(id):
            environ_obj = Environment.objects
            environ_info = environ_obj.filter(id=id)
            update_time=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
            try:
                environ_info.update(path_name=path_name,host=host,port=port,envir_descript=envir_descript,update_time=update_time)
                context = {'success': '编辑环境成功咯！'}
            except:
                context = {'success':'编辑环境失败了'}
        return JsonResponse(context)

@login_check
def environDelete(request,id):
    if request.method =='GET':
        if len(id) > 0:
            Environment.objects.filter(id=id).delete()
            context={"success":"删除成功！"}
            return  JsonResponse(context)
    elif request.is_ajax():
        ##删除所有
        ids =request.POST.get("ids")
        ids = eval(ids)
        if type(ids) != int:
            for id in ids:
                Environment.objects.filter(id=id).delete()
            context = {"success": "删除成功！"}
        else:
            Environment.objects.filter(id=ids).delete()
            context = {"success": "删除成功！"}
        return JsonResponse(context)

@login_check
def isEnable(request,id):
    if len(id) > 0:
        environ = Environment.objects.filter(id=id)
        if environ[0].status == 1:
            environ.update(status=2)
            context = {"success": "已停用！","icon":5}
        else:
            environ.update(status=1)
            context = {"success": "已启用！","icon":6}
        return  JsonResponse(context)


'''测试用例管理'''
def testCaseManager(request,id):
    if request.method == 'GET':
        testCase = TestCase.objects
        testCaseList = testCase.all().order_by('id')
        paginator = Paginator(testCaseList, 8)
        firstPage =id
        #默认id的值传递为0
        if int(firstPage) > 0:
            pages = paginator.page(int(firstPage))
        else:
            firstPage =1
            pages = paginator.page(1)
        testCaseList =pages.object_list
        environ = Environment.objects
        environList = environ.all()

        context = {'testCaseList':testCaseList,'pageList':paginator,'currentPag':int(firstPage),"pages":pages,"title":"测试环境管理","environList":environList}
        return  render(request,'testCase-list.html',context)


'''用例新增'''
@login_check
def TestcaseAdd(request):
    if request.method == 'GET':
        #testcaseIds = TestCase.objects.all().values("id")
        testcaseInfo = TestCase.objects.all()

        context={'title':'测试用例新增','btn':'增加','testcaseInfo':testcaseInfo}
        return  render(request,'testcase-add.html',context)
    if request.method == 'POST':
        params= eval(request.body)
        case_name = params.get('case_name','')
        req_path = params.get('req_path','')
        req_method =params.get('req_method', '')
        req_param = params.get('req_param', '')
        req_exceptResult = params.get('except_result','')
        case_id = params.get('case_id')
        resp_data = params.get('resp_data')
        dataFormat = params.get('dataFormat')
        username = request.session.get("username",'')
        testcase = TestCase.objects
        if len(case_name) >0 and len(req_path) and len(req_method):
            testcase.create(case_name=case_name,req_path=req_path,req_method=req_method,req_param=req_param,
                            username=username,except_result=req_exceptResult,case_id=case_id,resp_data=resp_data,dataFormat=dataFormat)
            context={'success':'添加成功啦'}
            return  JsonResponse(context)

        else:
            context = '添加失败了，请重新添加'
            return JsonResponse({'success':context})

@login_check
def testCaseEdit(request,id):
    if request.method == 'GET':
        testcase =TestCase.objects
        testcase_info = testcase.get(id=id)
        testcaseInfo = TestCase.objects.all()
        context = {'testcase_info': testcase_info, 'btn': '编辑','id': id,"testcaseInfo":testcaseInfo}
        return render(request,'testcase-add.html',context)
    elif request.is_ajax():
        params = eval(request.body)
        case_name = params.get('case_name', '')
        req_path = params.get('req_path', '')
        req_method = params.get('req_method', '')
        req_param = params.get('req_param', '')
        req_exceptResult = params.get('except_result', '')
        case_id = params.get('case_id')
        resp_data = params.get('resp_data')
        dataFormat = params.get('dataFormat')
        username = request.session.get("username", '')

        if int(id):
            testcase_obj = TestCase.objects
            testcase_info = testcase_obj.filter(id=id)
            update_time=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
            try:
                testcase_info.update(case_name=case_name,req_path=req_path,req_method=req_method,req_param=req_param,
                            username=username,except_result=req_exceptResult,case_id=case_id,resp_data=resp_data,dataFormat=dataFormat,update_time=update_time)
                context = {'success': '修改用例成功咯！'}
            except:
                context = {'success':'修改用例失败了'}
        return JsonResponse(context)


def testcaseDelete(request,id):
    if request.method == 'GET':
        if len(id) > 0:
            TestCase.objects.filter(id=id).delete()
            context = {"success": "删除成功！"}
            return JsonResponse(context)
    elif request.is_ajax():
        ##删除所有
        ids = request.POST.get("ids")
        ids = eval(ids)
        if type(ids) != int:
            for id in ids:
                TestCase.objects.filter(id=id).delete()
            context = {"success": "删除成功！"}
        else:
            context = {"success": "删除成功！"}
            TestCase.objects.filter(id=ids).delete()
        return JsonResponse(context)
    pass


'''新增'''
@login_check
def getTestCaseInfo(request,id):
    testcaseInfo = TestCase.objects.filter(id=id)
    json_data = serializers.serialize("json", testcaseInfo)
    context = {'testcaseInfo': json_data}
    return JsonResponse(context)




ids =[]
'''递归查找依赖的用例数据，运行'''
def runAsCase(id,url):
        testcaseInfo = TestCase.objects.get(id=id)
        if len(testcaseInfo.case_id) == 0:
            #第一条用例不需要依赖父类数据，第一条用例就是父类
            reposeText = params(id,url,"")

            ids.reverse()
            for i in range(0,len(ids)):
                if i == len(ids) - 1:
                    reposeText = params(ids[i], url, reposeText)
                    return reposeText
                reposeText = params(ids[i], url, reposeText)

        else:
            ids.append(id)
            runAsCase(id=testcaseInfo.case_id,url=url)

def params(id,url,needParentData):
        # 先执行好case_id的用例，取出resp_data数据,在附加到id用例的执行
        testcaseInfo = TestCase.objects.filter(id=id)
        urls = url.split("/")
        url = urls[0] + "//" + urls[2] + testcaseInfo.req_path
        response = requests.get(url, params=testcaseInfo.req_param)
        if needParentData:
            json = needParentData #父类json数据
            json_exec = parse(testcaseInfo.resp_data)
            male = json_exec.find(json)
            reposeText = [match.value for match in male]
            print(reposeText)
            return  reposeText  #得到依赖数据
        # 执行完第一条用例后，获取的返回值在递归去
        return response.content




def runTest(request):
    runAsCase(3,"http://www.baidu.com/")



'''执行测试用例'''
def runCase(testcaseInfo,url,method,params,except_result,**kwargs):
        try:
            if method == 'GET':
                if len(kwargs):
                    #先执行好case_id的用例，取出resp_data数据,在附加到id用例的执行
                    testcaseInfoChild = TestCase.objects.get(id= kwargs['case_id'])
                    urls = url.split("/")

                    #根据服务器返回的数据格式:JSON XML HTML格式
                    #testcaseInfo = TestCase.objects.get(id=id)
                    if testcaseInfo.dataFormat == "JSON":
                        childResp =  testcaseInfoChild.resp_result
                        resp_data = testcaseInfo.resp_data
                        childResp = json.loads(childResp)

                        #json = {"msg": "success", "repo": {'sid': 8999901, 'moviesList': ['电影1', '电影2', '电影3']}}
                        json_exec = parse(resp_data+'')
                        male = json_exec.find(childResp)
                        values = [match.value for match in male]

                        dic ={}
                        dic[resp_data+'']=values
                        params = str(dic)

                        response = requests.get(url, params=params)
                    else:
                        pass





                else:
                    response = requests.get(url,params=params)
            elif method == 'POST':
                response = requests.post(url, params=params)
            elif method =='PUT':
                response = requests.put(url, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, params=params)

            if response.status_code == 200:
              try:
                if response.headers['content-type']=='text/html':
                    list = re.findall(except_result,response.content.decode("utf8","ignore"))
                    if len(list):
                        info1 = "恭喜,用例执行成功了"
                        content = {"info": info1, "statu": "success"}
                        testcaseInfo = TestCase.objects.filter(id=testcaseInfo.id)
                        update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                        testcaseInfo.update(resp_result=response.content.decode("utf8", "ignore"),update_time=update_time, test_result=1)
                        return JsonResponse(content)
                    else:
                        content = {"info": "用例执行失败,预期结果和响应结果不一致！", "statu": "error"}
                        testcaseInfo = TestCase.objects.filter(id=testcaseInfo.id)
                        update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                        testcaseInfo.update(resp_result=response.content.decode("utf8", "ignore"),
                                            update_time=update_time, test_result=1)
                        return JsonResponse(content)
                else:
                    assert except_result in response.content.decode("utf8","ignore")
                    info1="恭喜,用例执行成功了"
                    content={"info":info1,"statu":"success"}
                    testcaseInfo = TestCase.objects.filter(id=testcaseInfo.id)
                    update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    testcaseInfo.update(resp_result=response.content.decode("utf8","ignore"),update_time=update_time,test_result=1)
                    return JsonResponse(content)
              except AssertionError as e:
                 print(e)
                 content = {"info": "用例执行失败,预期结果和响应结果不一致！","statu":"error"}
                 testcaseInfo = TestCase.objects.filter(id=testcaseInfo.id)
                 update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                 testcaseInfo.update(resp_result=response.content.decode("utf8","ignore"), update_time=update_time, test_result=2)
                 return JsonResponse(content)
            else:
                  content = {"info": "请求返回的状态不是200,尽快查看日志看看错误信息！","statu":"error"}
                  testcaseInfo = TestCase.objects.filter(id=testcaseInfo.id)
                  update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                  testcaseInfo.update(resp_result=response.content.decode("utf8","ignore"), update_time=update_time, test_result=2)
                  return JsonResponse(content)
        except BaseException as e:
            content = {"info": "请检测请求地址是否正确,执行发送请求出现异常了！异常信息是:"+str(e),"statu":"error"}
            testcaseInfo = TestCase.objects.filter(id=testcaseInfo.id)
            update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            testcaseInfo.update(resp_result=str(e),update_time=update_time, test_result=2)
            return JsonResponse(content)

'''页面跑用例的方法'''
@login_check
def execute_cases(request,id):
    if request.method =="POST":
        postdataDic = eval(request.body)
        method =postdataDic.get("req_method","")
        requestPath = postdataDic.get("req_path","")
        params = postdataDic.get("req_param","")
        except_result = postdataDic.get("except_result","")
        case_id = postdataDic.get("case_id","")
        resp_data = postdataDic.get("resp_data","")

        testcaseInfo = TestCase.objects.get(id=id)

        #执行测试用例
        if testcaseInfo.case_id:
            return runCase(testcaseInfo=testcaseInfo,url=requestPath,method=method,params=params,except_result=except_result,case_id=testcaseInfo.case_id,resp_data=resp_data)
        else:
            return runCase(testcaseInfo=testcaseInfo, url=requestPath, method=method, params=params, except_result=except_result)





def test_bet(request):
    if request.method == 'GET':
        return render(request,"testbet_add.html")
    elif request.is_ajax():
        url = request.POST.get('url')
        username = request.POST.get('username')
        passsword = request.POST.get('password')

        return