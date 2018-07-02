from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.views.generic.edit import FormView
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
import json
from datetime import datetime
from tablib import Dataset
from .models import Transaction, Header, Ticker
from .forms import TickerForm, HeaderForm, BrokerForm, OutputForm, TradeMatchForm
from django.db import transaction, DatabaseError
import django_tables2 as tables
from django_tables2 import RequestConfig

# Create your views here.

def conv_input(import_data):
    headL = []
    clfs = False
    ioi = False
    dictHead = {}
    outSet = Dataset()
    #Pull header mapping from database
    modelHead = Header.objects.all()
    for j in modelHead:
        dictHead[j.inp_head] = j.out_head

    for i in import_data.headers:
        if "C.L.F.S., Ltd." in str(i):
            clfs = True
        if "Deal_Type" in str(i):
            ioi = True

    dictH = {'prim_key':-1, 'type':-1, 'transtype':-1, 'symbol':-1, 'tradedate':-1, 'broker':-1, 'shareamount':-1,
    'buyprice':-1, 'sellprice':-1, 'commiss':-1, 'dealsize':-1, 'dealprice':-1, 'leadbroker':-1, 'percsellhold':-1, 'opentraddat':-1,
    'vwaptraddat':-1, 'closetraddat':-1, 'prevclose':-1, 't2close':-1, 't3close':-1, 't4close':-1, 't5close':-1, 'spopen':-1, 'spclose':-1}

    dictTick = {}

    tickers = Ticker.objects.all()
    for j in tickers:
        dictTick[j.inp_ticker] = j.standard_ticker

    if clfs:
        firstLine = True
        count  = 0
        for i in import_data:
            if firstLine:
                topL = list(i)
                botL = list(i)
                firstLine = False
            else:
                dataL = list(i)
                if dataL[0] is not None:
                    if "---" in dataL[0]:
                        firTr = count + 4
                        for j in range(0, len(topL)):
                            if topL[j] is not None:
                                headL.append(topL[j] + " " + botL[j])
                            else:
                                headL.append(botL[j])
                topL = botL
                botL = dataL
            count += 1

        count = 0

        for i in headL:
            if i in dictHead:
                if dictHead[i] in dictH:
                    dictH[dictHead[i]] = count
            count += 1

        count = 0
        headList = []

        for i in dictH:
            headList.append(i)

        outSet.headers = headList

        for i in import_data:
            if count >= firTr:
                outList = []
                dat = list(i)
                for j in dictH:
                    if dictH[j] != -1:
                        val = dat[dictH[j]]
                        if val in dictTick:
                            val = dictTick[val]
                        if val == 'by':
                            val = "Buy"
                        if val == 'sl':
                            val = "Sell"
                        outList.append(val)
                    elif j == 'prim_key':
                        outList.append(dat[0] + '||' + dat[1] + '|' + str(dat[2]).replace(' ','_') + '|' + str(dat[4]))
                    else:
                        outList.append(None)

                outSet.append(tuple(outList))

            count += 1
        return(outSet)
    elif ioi:
        count = 0
        headL = list(import_data.headers)

        for i in headL:
            if i in dictHead:
                if dictHead[i] in dictH:
                    if dictH[dictHead[i]] == -1:
                        dictH[dictHead[i]] = count
                    else:
                        dictH[dictHead[i]] = str(dictH[dictHead[i]]) +  "|" + str(count)
            count += 1

        count = 0
        headList = []

        for i in dictH:
            headList.append(i)

        outSet.headers = headList

        for i in import_data:
            outList = []
            dat = list(i)
            if dat[0] is not None:
                for j in dictH:
                    if dictH[j] != -1:
                        if not isinstance(dictH[j], str):
                            val = dat[dictH[j]]
                        else:
                            vals = dictH[j].split("|")
                            res = 0
                            for k in vals:
                                if dat[int(k)] is not None:
                                    res += dat[int(k)]

                            val = str(res)

                        if val in dictTick:
                            val = dictTick[val]

                        if j == "symbol":
                            if " " in val:
                                val = str(val).replace(" ", "|")

                        outList.append(val)
                    elif j == 'prim_key':
                        if dat[6] is not None and dat[7] is not None:
                            shrs = dat[6] + dat[7]
                        elif dat[7] is None:
                            shrs = dat[6]
                        elif dat[6] is None:
                            shrs = dat[7]
                        else:
                            shrs = 0

                        print(dat[0], dat[2], shrs)
                        outList.append(dat[0] + '|' + dat[1] + '|' + str(dat[2]).replace(' ', '|') + '|' + str(dat[3]).replace(' ','_') + '|' + str(shrs))
                    else:
                        outList.append(None)

                outSet.append(tuple(outList))

                count += 1

        return(outSet)

@login_required
def index(request):
    """
    View function for Home Page of site.
    """
    return render(request, 'index.html', context = {})

class TradeMatchView(CreateView):
    template_name = 'trade_match.html'
    model = Transaction
    form_class = TradeMatchForm
    success_url = reverse_lazy('trade_match')

    def get(self, request):
        form = TradeMatchForm

        return render(request, 'trade_match.html', {'tradeForm': TradeMatchForm})

    def post(self, request):
        form = TradeMatchForm
        passVal = request.POST.dict()
        buys = request.POST.getlist('matched_trades')

        passVal = request.POST.dict()

        sharesmatched = 0
        trL = []

        for i in buys:
            print(i)
            matchK = ""
            trL = i.split("|")
            for j in range(0, 5):
                if j < 4:
                    matchK += trL[j] + "|"
                else:
                    matchK += trL[j]

            if Transaction.objects.filter(prim_key=matchK).exists():
                shares = int(trL[5])
                j  = Transaction.objects.get(prim_key=matchK)
                if j.matching is not None:
                    j.matching += ";" + passVal['saleF'] + "|" + str(shares)
                    j.matching_amount += int(shares)
                else:
                    print(passVal['saleF'])
                    j.matching = passVal['saleF'] + "|" + str(shares)
                    j.matching_amount = int(shares)

                print(j.matching, j.matching_amount)
                j.save()

                sharesmatched += int(shares)

        sale = Transaction.objects.get(prim_key=passVal['saleF'])

        if sale.matching_amount is not None:
            soldSh = shares
            soldSh += int(sharesmatched)
            sale.matching_amount = soldSh
            sale.save()
        else:
            soldSh = shares
            sale.matching_amount = soldSh
            sale.save()

        if sale.shareamount == sale.matching_amount:
            sale.matching = 'Matched'
            sale.save()

        form = TradeMatchForm

        return render(request, 'trade_match.html', {'tradeForm': TradeMatchForm})

def load_purchases(request):
    sale_trade = request.GET.get('saleF')

    passVal = request.GET.dict()
    prim_k = passVal['purchases']
    saleTr = prim_k.split("|")
    saleSym = saleTr[2]
    saleAm = saleTr[4]

    dPurchases = {}

    for i in Transaction.objects.filter(type='Buy').filter(symbol=saleSym).filter(shareamount__lte=saleAm).values():
        if i['shareamount'] != i['matching_amount']:
            if i['matching_amount'] is None:
                matchedSh = 0
            else:
                matchedSh = int(i['matching_amount'])

            if i['prim_key'] in dPurchases:
                dPurchases[i['prim_key']].append(str(i['symbol']) + " " + str(int(i['shareamount']) - matchedSh) + " Shares Bought " + str(i['tradedate']))
            else:
                dPurchases[i['prim_key']] = [str(i['symbol']) + " " + str(int(i['shareamount']) - matchedSh) + " Shares Bought " + str(i['tradedate'])]

    data = json.dumps(dPurchases)

    return JsonResponse(data, safe=False)

#Input Functions

class TickerTable(tables.Table):
    class Meta:
        model = Ticker

class HeaderTable(tables.Table):
    class Meta:
        model = Header

@login_required
def input_data(request):
    """
    View function for Input Page of site.
    """
    tickTable = TickerTable(Ticker.objects.all())
    RequestConfig(request, paginate={'per_page': 5}).configure(tickTable)

    headTable = HeaderTable(Header.objects.all())
    RequestConfig(request, paginate={'per_page': 5}).configure(headTable)

    tForm = TickerForm(request.user)
    hForm = HeaderForm(request.user)
    bForm = BrokerForm(request.user)

    if request.method == 'POST':
        postdict = request.POST.dict()

        print(postdict)

        if 'trade_file' in postdict:
            dataset = Dataset()
            trade_data = request.FILES['datafile']
            imported_data = dataset.load(trade_data.read(),format='xlsx')

            conv_data = conv_input(imported_data)

            recordList = []

            for j in conv_data:
                data = list(j)
                i = Transaction()
                i.prim_key = data[0]
                i.type = data[1]
                i.transtype = data[2]
                i.symbol = data[3]
                i.tradedate = data[4]
                i.broker = data[5]
                i.shareamount = data[6]
                i.buyprice = data[7]
                i.sellprice = data[8]
                i.commiss = data[9]
                i.dealsize = data[10]
                i.dealprice = data[11]
                i.leadbroker = data[12]
                i.percsellhold = data[13]
                i.opentraddat = data[14]
                i.vwaptraddat = data[15]
                i.closetraddat = data[16]
                i.prevclose = data[17]
                i.t2close = data[18]
                i.t3close = data[19]
                i.t4close = data[20]
                i.t5close = data[21]
                i.spopen = data[22]
                i.spclose = data[23]

                recordList.append(i)

            #with transaction.atomic():
                # Loop over each store and invoke save() on each entry
            for i in recordList:
                # save() method called on each member to create record
                i.save()
        elif 'tickUpdate' in postdict:
            tick = Ticker()
            tick.inp_ticker = postdict['inpTick']
            tick.standard_ticker = postdict['outTick']
            tick.save()

            tDict = {}
            ticks = Ticker.objects.all()
            for i in ticks:
                if i.inp_ticker not in tDict:
                    print(i.inp_ticker)
                    tDict[i.inp_ticker] = i.standard_ticker

            trans = Transaction.objects.all()

            for i in trans:
                if i.symbol in tDict:
                    i.symbol = tDict[i.symbol]
                    i.save()

            tickTable = TickerTable(Ticker.objects.all())
            RequestConfig(request, paginate={'per_page': 5}).configure(tickTable)
        elif 'headUpdate' in postdict:
            head = Header()
            head.inp_head = postdict['inpHead']
            head.out_head = postdict['outHead']
            head.save()

            headTable = HeaderTable(Header.objects.all())
            RequestConfig(request, paginate={'per_page': 5}).configure(headTable)


    return render(request, 'input_data.html', context = {'TickTable':tickTable, 'HeadTable':headTable, 'tickForm':tForm, 'headForm':hForm, 'brokForm':bForm})


# Output Functions

def populate_output_table(purch_data, typ):
        outTable = []

        if typ == "IPO" or typ == "2nd":
            datHeads = ['tradedate', 'symbol', 'transtype', 'shareamount', 'buyprice', 'buy_total', 'sell_price', 'sell_total', 'commiss', 'gain_loss']

            heads = [('tradedate', tables.Column('Date', footer='Total:')), ('symbol', tables.Column('Ticker')), ('transtype', tables.Column('Type')), ('shareamount', tables.Column('Shares')), ('buyprice', tables.Column('Buy Price'))
            , ('buy_total', tables.Column('Buy Total $', footer=lambda table: sum(float(str(x['buy_total']).replace("$", "").replace(",","")) for x in table.data))), ('sell_price', tables.Column('Sell Price')),
            ('sell_total', tables.Column('Sell Total $', footer=lambda table: sum(float(str(x['sell_total']).replace("$", "").replace(",","")) for x in table.data))), ('commiss', tables.Column('Sell Commission $')) ,
            ('gain_loss', tables.Column('Gain/Loss', footer=lambda table: sum(float(str(x['gain_loss']).replace("$", "").replace(",","")) for x in table.data)))]

            matchedSales= []

            for i in purch_data.values():
                if ';' not in i['matching']:
                    saleDetails = i['matching'].split("|")
                    sharesSold = saleDetails[5]
                    primK = ""
                    for k in range(0, 5):
                        if k != 4:
                            primK += saleDetails[k] + "|"
                        else:
                            primK += saleDetails[k]
                    sale_Trans = Transaction.objects.get(prim_key=primK)
                    matchedSales.append((sale_Trans, sharesSold))
                else:
                    for l in i['matching'].split(";"):
                        saleDetails = l.split("|")
                        sharesSold = saleDetails[5]
                        primK = ""
                        for k in range(0, 5):
                            if k != 4:
                                primK += saleDetails[k] + "|"
                            else:
                                primK += saleDetails[k]
                        sale_Trans = Transaction.objects.get(prim_key=primK)
                        matchedSales.append((sale_Trans, sharesSold))

                rowDict = {}
                avgSalePr = 0
                shareTot = 0
                saleTot = 0

                for k in matchedSales:
                    matSale = k[0]
                    matShare = int(k[1])
                    avgSalePr += float(matSale.sellprice) * matShare
                    shareTot += matShare
                    saleTot += matShare * float(matSale.sellprice)


                for j in datHeads:
                    datDict = {}

                    if j in i:
                        if j == 'buyprice' or j =='commiss':
                            datDict[j] = '${:,.2f}'.format(i[j])
                        else:
                            datDict[j] = i[j]
                    elif j == 'sell_price':
                        if shareTot != 0:
                            salePr = avgSalePr / shareTot
                            datDict[j] = '${:,.2f}'.format(avgSalePr / shareTot)
                    elif j == 'buy_total':
                        datDict[j] = '${:,.2f}'.format(float(i['shareamount']) * float(i['buyprice']))
                    elif j == 'sell_total':
                        datDict[j] = '${:,.2f}'.format(saleTot)
                    elif j == 'gain_loss':
                        datDict[j] = '${:,.2f}'.format(float(i['matching_amount']) * (salePr - float(i['buyprice'])))

                    rowDict.update(datDict)

                outTable.append(rowDict)

            table = TransactionTable(outTable, extra_columns=heads)
            return(table)
        elif typ == "Trade":
            datHeads = ['tradedate', 'symbol', 'transtype', 'shareamount', 'buyprice', 'buy_commiss', 'sell_price', 'commiss']

            heads = [('tradedate', tables.Column('Date', footer='Total:')), ('symbol', tables.Column('Ticker')), ('transtype', tables.Column('Type')), ('shareamount', tables.Column('Shares')), ('buyprice', tables.Column('Buy Price'))
            , ('buy_commiss', tables.Column('Buy Commission')), ('sell_price', tables.Column('Sell Price')), ('commiss', tables.Column('Sell Commission $'))]

            matchedSales= []

            for i in purch_data.values():
                rowDict = {}
                avgSalePr = 0
                shareTot = 0
                saleTot = 0

                if i['matching'] is not None:
                    if ';' not in i['matching']:
                        saleDetails = i['matching'].split("|")
                        sharesSold = saleDetails[5]
                        primK = ""
                        for k in range(0, 5):
                            if k != 4:
                                primK += saleDetails[k] + "|"
                            else:
                                primK += saleDetails[k]
                        sale_Trans = Transaction.objects.get(prim_key=primK)
                        matchedSales.append((sale_Trans, sharesSold))
                    else:
                        for l in i['matching'].split(";"):
                            saleDetails = l.split("|")
                            sharesSold = saleDetails[5]
                            primK = ""
                            for k in range(0, 5):
                                if k != 4:
                                    primK += saleDetails[k] + "|"
                                else:
                                    primK += saleDetails[k]
                            sale_Trans = Transaction.objects.get(prim_key=primK)
                            matchedSales.append((sale_Trans, sharesSold))

                    rowDict = {}
                    avgSalePr = 0
                    shareTot = 0
                    saleTot = 0

                    for k in matchedSales:
                        matSale = k[0]
                        matShare = int(k[1])
                        avgSalePr += float(matSale.sellprice) * matShare
                        shareTot += matShare
                        saleTot += matShare * float(matSale.sellprice)

                for j in datHeads:
                    datDict = {}

                    if j in i:
                        if j == 'buyprice' or j =='commiss':
                            if j == 'commiss' and i['type'] == 'Sell':
                                datDict[j] = '${:,.2f}'.format(i[j])
                            elif j == 'buyprice':
                                datDict[j] = '${:,.2f}'.format(i[j])
                        else:
                            datDict[j] = i[j]
                    elif j == 'sell_price':
                        if shareTot != 0:
                            salePr = avgSalePr / shareTot
                            datDict[j] = '${:,.2f}'.format(avgSalePr / shareTot)
                    elif j == 'buy_commiss' and i['type'] == 'Buy':
                        datDict[j] = '${:,.2f}'.format(i['commiss'])

                    rowDict.update(datDict)

                outTable.append(rowDict)

            table = TransactionTable(outTable, extra_columns=heads)
            return(table)

def populate_open_pos_table(openPosList):
    outTable = []
    datHeads = ['symbol', 'transtype', 'open_pos']

    heads = [('symbol', tables.Column('Symbol')), ('transtype', tables.Column('Type')), ('open_pos', tables.Column('Open Position'))]

    for i in openPosList:
        rowDict = {}

        for j in datHeads:
            datDict = {}

            if j == 'symbol':
                datDict[j] = i[0]
            elif j == 'transtype':
                datDict[j] = i[1]
            elif j == 'open_pos':
                datDict[j] = i[2]

            rowDict.update(datDict)
        outTable.append(rowDict)

    table = OpenPosTable(outTable, extra_columns=heads)
    return(table)

class TransactionTable(tables.Table):
    paginate_by = 10

class OpenPosTable(tables.Table):
    paginate_by = 5


class OutputData(FormView):
    template_name = 'output.html'
    form_class = OutputForm

    def get(self, request):
        oForm = OutputForm()
        openPos = []

        ipo_table = populate_output_table(Transaction.objects.none(), "IPO")
        RequestConfig(request, paginate={'per_page': 10}).configure(ipo_table)

        sec_table = populate_output_table(Transaction.objects.none(), "2nd")
        RequestConfig(request, paginate={'per_page': 10}).configure(sec_table)

        trade_table = populate_output_table(Transaction.objects.none(), "Trade")
        RequestConfig(request, paginate={'per_page': 10}).configure(trade_table)

        op_Pos_Table = populate_open_pos_table(openPos)
        RequestConfig(request, paginate={'per_page': 3}).configure(op_Pos_Table)

        return render(request, 'output.html', context = {'OutForm':oForm, 'OpenPositionTable':op_Pos_Table, 'ipoTable':ipo_table, 'secTable':sec_table, 'Trade_Table':trade_table})

    def post(self, request):
        oForm = OutputForm()
        openPos = []

        passVal = request.POST.dict()

        out_broker = passVal['brok']
        out_sd = datetime.strptime(passVal['start_date'], '%m/%d/%Y')
        out_ed = datetime.strptime(passVal['end_date'], '%m/%d/%Y')

        out_trades = Transaction.objects.filter(broker=out_broker).filter(tradedate__gte=out_sd).filter(tradedate__lte=out_ed).values()
        IPOPL = 0
        secPL = 0
        commiss = 0

        for i in out_trades:
            if i['type'] == "Buy" and i['matching_amount'] != i['shareamount'] and i['shareamount'] != 0:
                if i['matching_amount'] is None:
                    openPos.append((i['symbol'], i['transtype'], i['shareamount']))
                else:
                    openPos.append((i['symbol'], i['transtype'], int(i['shareamount']) - int(i['matching_amount'])))

        op_Pos_Table = populate_open_pos_table(openPos)
        RequestConfig(request, paginate={'per_page': 3}).configure(op_Pos_Table)
        #Update

        matchedSalesIPO = []
        openPos = []

        for i in out_trades:
            if i['type'] == "Buy" and i['transtype'] == 'IPO' and i['matching'] is not None:
                if ';' not in i['matching']:
                    saleDetails = i['matching'].split("|")
                    sharesSold = saleDetails[5]
                    primK = ""
                    for k in range(0, 5):
                        if k != 4:
                            primK += saleDetails[k] + "|"
                        else:
                            primK += saleDetails[k]
                    matched_sell = Transaction.objects.get(prim_key=primK)

                    matchedSalesIPO.append((matched_sell, sharesSold))
                else:
                    for l in i['matching'].split(";"):
                        saleDetails = l.split("|")
                        sharesSold = saleDetails[5]
                        primK = ""
                        for k in range(0, 5):
                            if k != 4:
                                primK += saleDetails[k] + "|"
                            else:
                                primK += saleDetails[k]
                        matched_sell = Transaction.objects.get(prim_key=primK)
                        matchedSalesIPO.append((matched_sell, sharesSold))

                avgPr = 0
                sharesSold = 0
                for k in matchedSalesIPO:
                    avgPr += float(k[0].sellprice) * int(k[1])
                    sharesSold += int(k[1])
                    commiss += int(k[0].commiss)
                if sharesSold != 0:
                    avgSlPr = avgPr / sharesSold
                else:
                    avgSlPr = 0

                IPOPL += (float(avgSlPr) - float(i['buyprice'])) * float(i['matching_amount'])


        ipo_table = populate_output_table(Transaction.objects.filter(broker=out_broker).filter(tradedate__gte=out_sd).filter(tradedate__lte=out_ed)
        .filter(type='Buy').filter(transtype='IPO').exclude(matching=None), "IPO")

        RequestConfig(request, paginate={'per_page': 10}).configure(ipo_table)

        #update

        matchedSalesSec = []

        for i in out_trades:
            if i['type'] == "Buy" and (i['transtype'] == '2nd' or i['transtype'] == 'O/N') and i['matching'] is not None:
                if ';' not in i['matching']:
                    saleDetails = i['matching'].split("|")
                    sharesSold = saleDetails[5]
                    primK = ""
                    for k in range(0, 5):
                        if k != 4:
                            primK += saleDetails[k] + "|"
                        else:
                            primK += saleDetails[k]
                    matched_sell = Transaction.objects.get(prim_key=primK)

                    matchedSalesSec.append((matched_sell, sharesSold))
                else:
                    for l in i['matching'].split(";"):
                        saleDetails = l.split("|")
                        sharesSold = saleDetails[5]
                        primK = ""
                        for k in range(0, 5):
                            if k != 4:
                                primK += saleDetails[k] + "|"
                            else:
                                primK += saleDetails[k]
                        matched_sell = Transaction.objects.get(prim_key=primK)
                        matchedSalesSec.append((matched_sell, sharesSold))

                avgPr = 0
                sharesSold = 0
                for k in matchedSalesSec:
                    avgPr += float(k[0].sellprice) * int(k[1])
                    sharesSold += int(k[1])
                    commiss += int(k[0].commiss)
                if sharesSold != 0:
                    avgSlPr = avgPr / sharesSold
                else:
                    avgSlPr = 0

                secPL += (float(avgSlPr) - float(i['buyprice'])) * float(i['matching_amount'])

        sec_table = populate_output_table(Transaction.objects.filter(broker=out_broker).filter(tradedate__gte=out_sd).filter(tradedate__lte=out_ed)
        .filter(type='Buy').filter(Q(transtype='2nd') | Q(transtype='O/N')).exclude(matching=None), "2nd")

        RequestConfig(request, paginate={'per_page': 10}).configure(sec_table)

        matchedSalesTrades = []

        for i in out_trades:
            if i['type'] == "Buy" and i['transtype'] == 'Trade' and i['matching'] is not None:
                if ';' not in i['matching']:
                    saleDetails = i['matching'].split("|")
                    sharesSold = saleDetails[5]
                    primK = ""
                    for k in range(0, 5):
                        if k != 4:
                            primK += saleDetails[k] + "|"
                        else:
                            primK += saleDetails[k]
                    matched_sell = Transaction.objects.get(prim_key=primK)

                    matchedSalesTrades.append((matched_sell, sharesSold))
                else:
                    for l in i['matching'].split(";"):
                        saleDetails = l.split("|")
                        sharesSold = saleDetails[5]
                        primK = ""
                        for k in range(0, 5):
                            if k != 4:
                                primK += saleDetails[k] + "|"
                            else:
                                primK += saleDetails[k]
                        matched_sell = Transaction.objects.get(prim_key=primK)
                        matchedSalesTrades.append((matched_sell, sharesSold))

        trade_table = populate_output_table(Transaction.objects.filter(broker=out_broker).filter(tradedate__gte=out_sd).filter(tradedate__lte=out_ed)
        .filter(type='Buy').filter(transtype='Trade'), "Trade")
        RequestConfig(request, paginate={'per_page': 10}).configure(trade_table)

        totPL = IPOPL + secPL
        if totPL != 0:
            netPerc = commiss / totPL
        else:
            netPerc = 0

        return render(request, 'output.html', context = {'OutForm':oForm, 'OpenPositionTable':op_Pos_Table, 'IPO_PL':'${:,.2f}'.format(IPOPL), 'ipoTable':ipo_table, 'Sec_PL':'${:,.2f}'.format(secPL), 'secTable':sec_table,
        'commis':'${:,.2f}'.format(commiss), 'Net_Perc':"{:.2%}".format(netPerc), 'Total_PL':'${:,.2f}'.format(totPL), 'Trade_Table':trade_table})

class SummaryTable(tables.Table):
    paginate_by = 20

def populate_summary_table(summaryList):
    outTable = []
    datHeads = ['broker', 'IPO PL', '2nd ON', 'Total', 'commiss', 'Net', 'Pref Commissions']

    heads = [('broker', tables.Column('Broker')), ('IPO PL', tables.Column('IPO P&L')), ('2nd ON', tables.Column('2nd Overnight P&L')),
    ('Total', tables.Column('Total P&L')), ('commiss', tables.Column('Commissions')), ('Net', tables.Column('Net P&L')), ('Pref Commissions', tables.Column('Pref Commissions'))]

    for i in summaryList:
        rowDict = {}

        for j in datHeads:
            datDict = {}

            if j == 'broker':
                datDict[j] = i[0]
            elif j == 'IPO PL':
                datDict[j] = '${:,.2f}'.format(i[1])
            elif j == '2nd ON':
                datDict[j] = '${:,.2f}'.format(i[2])
            elif j == 'Total':
                datDict[j] = '${:,.2f}'.format(i[3])
            elif j == 'commiss':
                datDict[j] = '${:,.2f}'.format(i[4])
            elif j == 'Net':
                datDict[j] = '${:,.2f}'.format(i[5])

            rowDict.update(datDict)
        outTable.append(rowDict)

    table = SummaryTable(outTable, extra_columns=heads)
    return(table)


@login_required
def summary(request):
    """
    View function for Summary of site.
    """

    brokers = []
    all_trades = Transaction.objects.filter(type='Buy').values()

    for i in all_trades:
        if i['broker'] not in brokers:
            brokers.append(i['broker'])

    summList = []

    for i in brokers:
        IPOPL = 0
        secPL = 0
        commiss = 0

        for j in all_trades:
            if j['shareamount'] != 0:
                if j['broker'] == i:
                    commiss += j['commiss']
                    if j['transtype'] == 'IPO' and j['matching'] is not None:
                        if ';' not in j['matching']:
                            matchK = ""
                            trL = j['matching'].split("|")
                            for k in range(0, 5):
                                if k < 4:
                                    matchK += trL[k] + "|"
                                else:
                                    matchK += trL[k]
                            saleDets = Transaction.objects.get(prim_key=matchK)
                        #code for many matching sales
                        IPOPL += (saleDets.sellprice - j['buyprice']) * j['matching_amount']
                        commiss += saleDets.commiss
                    elif (j['transtype'] == '2nd' or j['transtype'] == 'ON') and j['matching'] is not None:
                        if ';' not in j['matching']:
                            matchK = ""
                            trL = j['matching'].split("|")
                            for k in range(0, 5):
                                if k < 4:
                                    matchK += trL[k] + "|"
                                else:
                                    matchK += trL[k]
                            saleDets = Transaction.objects.get(prim_key=matchK)
                        #code for many matching sales
                        secPL += (saleDets.sellprice - j['buyprice']) * j['matching_amount']
                        commiss += saleDets.commiss
        totPL = IPOPL + secPL
        netPL = totPL - commiss
        summList.append((i, IPOPL, secPL, totPL, commiss, netPL))

    print(summList)
    Summary_Table = populate_summary_table(summList)
    return render(request, 'summary.html', context ={'SummaryTable':Summary_Table})
