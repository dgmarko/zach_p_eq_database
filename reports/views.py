from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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
        print(outSet)
        return(outSet)
    elif ioi:
        count = 0
        headL = list(import_data.headers)

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
            outList = []
            dat = list(i)
            for j in dictH:
                if dictH[j] != -1:
                    val = dat[dictH[j]]
                    if val in dictTick:
                        val = dictTick[val]
                    outList.append(val)
                elif j == 'prim_key':
                    outList.append(dat[0] + '|' + dat[1] + '|' + dat[2] + '|' + str(dat[3]).replace(' ','_') + '|' + str(dat[6]))
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
                j.matching = passVal['saleF']
                j.matching_amount = int(shares)
                j.save()

                sharesmatched += int(shares)

        sale = Transaction.objects.get(prim_key=passVal['saleF'])

        if sale.matching_amount is not None:
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
            if i['prim_key'] in dPurchases:
                dPurchases[i['prim_key']].append(str(i['symbol']) + " " + str(i['shareamount']) + " Shares Bought " + str(i['tradedate']))
            else:
                dPurchases[i['prim_key']] = [str(i['symbol']) + " " + str(i['shareamount']) + " Shares Bought " + str(i['tradedate'])]

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
            '''
            try:
                imported_data = dataset.load(trade_data.read(),format='xlsx')
            except:
                pass
            try:
                imported_data = dataset.load(trade_data.read().decode('utf-8', errors='ignore'),format='xlsx')
            except:
                pass
            '''
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

            heads = [('tradedate', tables.Column('Date')), ('symbol', tables.Column('Ticker')), ('transtype', tables.Column('Type')), ('shareamount', tables.Column('Shares')), ('buyprice', tables.Column('Buy Price'))
            , ('buy_total', tables.Column('Buy Total $')), ('sell_price', tables.Column('Sell Price')), ('sell_total', tables.Column('Sell Total $')), ('commiss', tables.Column('Sell Commission $')) , ('gain_loss', tables.Column('Gain/Loss'))]

            for i in purch_data.values():
                if ';' not in i['matching']:
                    sale_Trans = Transaction.objects.get(prim_key=i['matching'])
                else:
                    #Code for multiple sells for a buy
                    sale_Trans = "Epes"

                rowDict = {}

                for j in datHeads:
                    datDict = {}

                    if j in i:
                        datDict[j] = i[j]
                    elif j == 'sell_price':
                        datDict[j] = sale_Trans.sellprice
                    elif j == 'buy_total':
                        datDict[j] = float(i['shareamount']) * float(i['buyprice'])
                    elif j == 'sell_total':
                        datDict[j] = float(sale_Trans.sellprice) * float(i['matching_amount'])
                    elif j == 'gain_loss':
                        datDict[j] = float(i['matching_amount']) * (float(sale_Trans.sellprice) - float(i['buyprice']))

                    rowDict.update(datDict)

                outTable.append(rowDict)

        table = TransactionTable(outTable, extra_columns=heads)
        return(table)

class TransactionTable(tables.Table):
    paginate_by = 10

    trade_date = tables.Column()


class OutputData(FormView):
    template_name = 'output.html'
    form_class = OutputForm

    def get(self, request):
        oForm = OutputForm()

        ipo_table = populate_output_table(Transaction.objects.none(), "IPO")
        RequestConfig(request, paginate={'per_page': 10}).configure(ipo_table)

        sec_table = populate_output_table(Transaction.objects.none(), "2nd")
        RequestConfig(request, paginate={'per_page': 10}).configure(sec_table)

        return render(request, 'output.html', context = {'OutForm':oForm, 'ipoTable':ipo_table, 'secTable':sec_table})

    def post(self, request):
        oForm = OutputForm()

        passVal = request.POST.dict()

        out_broker = passVal['brok']
        out_sd = datetime.strptime(passVal['start_date'], '%m/%d/%Y')
        out_ed = datetime.strptime(passVal['end_date'], '%m/%d/%Y')

        out_trades = Transaction.objects.filter(broker=out_broker).filter(tradedate__gte=out_sd).filter(tradedate__lte=out_ed).values()
        IPOPL = 0
        secPL = 0

        for i in out_trades:
            if i['type'] == "Buy" and i['transtype'] == 'IPO' and i['matching'] is not None:
                matched_sell = Transaction.objects.get(prim_key=i['matching'])
                #Need code for multiple sale matches

                IPOPL += (float(matched_sell.sellprice) - float(i['buyprice'])) * float(i['matching_amount'])

        ipo_table = populate_output_table(Transaction.objects.filter(broker=out_broker).filter(tradedate__gte=out_sd).filter(tradedate__lte=out_ed)
        .filter(type='Buy').filter(transtype='IPO').exclude(matching=None), "IPO")

        RequestConfig(request, paginate={'per_page': 10}).configure(ipo_table)

        for i in out_trades:
            if i['type'] == "Buy" and i['transtype'] == '2nd' and i['matching'] is not None:
                matched_sell = Transaction.objects.get(prim_key=i['matching'])
                #Need code for multiple sale matches

                secPL += (float(matched_sell.sellprice) - float(i['buyprice'])) * float(i['matching_amount'])

        sec_table = populate_output_table(Transaction.objects.filter(broker=out_broker).filter(tradedate__gte=out_sd).filter(tradedate__lte=out_ed)
        .filter(type='Buy').filter(transtype='2nd').exclude(matching=None), "2nd")

        RequestConfig(request, paginate={'per_page': 10}).configure(sec_table)


        return render(request, 'output.html', context = {'OutForm':oForm, 'IPO_PL':'${:,.2f}'.format(IPOPL), 'ipoTable':ipo_table, 'Sec_PL':'${:,.2f}'.format(secPL), 'secTable':sec_table})
