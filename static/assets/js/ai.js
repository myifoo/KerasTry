function AiTrain(id, chart, train_values){
    this.id = id
    this.index = 0
    this.predict_values = []
    this.train_values = train_values
    this.render_values = train_values.map(function(e, i){return [i, parseFloat(e)]})
    this.predict = []
    this.parameters = {
        "nnType": "simple",
        "predictType": "realtime",
        "percent": 0.8,
        "step": 0.001,
        "optimizer": "adam",
        "nnum": 20,
        "batchSize": 250,
        "epochs": 1000,
        "timeStep": 32,
        "values": train_values
    }
    this.chart = chart
    this.option = {
        tooltip: {
            trigger: 'axis'
        },
        title: {
            text: id
        },
        legend: {
            data: [],
            left: 'right'
        },
        grid: {
            show: false,
            left: '2%',
            right: '2%',
            bottom: '12%'
        },
        dataZoom: [{
            type: 'slider',
            show: true,
            xAxisIndex: [0],
            handleSize: 10,//滑动条的 左右2个滑动条的大小
            height: 8,//组件高度
            left: 30, //左边的距离
            right: 40,//右边的距离
            bottom: 30,//右边的距离
            handleColor: '#ddd',//h滑动图标的颜色
            handleStyle: {
                borderColor: "#cacaca",
                borderWidth: "1",
                shadowBlur: 2,
                background: "#ddd",
                shadowColor: "#ddd",
            },
            fillerColor: new echarts.graphic.LinearGradient(1, 0, 0, 0, [{
                //给颜色设置渐变色 前面4个参数，给第一个设置1，第四个设置0 ，就是水平渐变
                //给第一个设置0，第四个设置1，就是垂直渐变
                offset: 0,
                color: '#535556'
            }, {
                offset: 1,
                color: '#535556'
            }]),
            backgroundColor: '#ddd',//两边未选中的滑动条区域的颜色
            showDataShadow: false,//是否显示数据阴影 默认auto
            showDetail: false,//即拖拽时候是否显示详细数值信息 默认true
            handleIcon: 'M-292,322.2c-3.2,0-6.4-0.6-9.3-1.9c-2.9-1.2-5.4-2.9-7.6-5.1s-3.9-4.8-5.1-7.6c-1.3-3-1.9-6.1-1.9-9.3c0-3.2,0.6-6.4,1.9-9.3c1.2-2.9,2.9-5.4,5.1-7.6s4.8-3.9,7.6-5.1c3-1.3,6.1-1.9,9.3-1.9c3.2,0,6.4,0.6,9.3,1.9c2.9,1.2,5.4,2.9,7.6,5.1s3.9,4.8,5.1,7.6c1.3,3,1.9,6.1,1.9,9.3c0,3.2-0.6,6.4-1.9,9.3c-1.2,2.9-2.9,5.4-5.1,7.6s-4.8,3.9-7.6,5.1C-285.6,321.5-288.8,322.2-292,322.2z',
            filterMode: 'filter',
            start: 80,
            end: 100
        }
        ],
        xAxis: {
            type: 'value',
            show: false
        },
        yAxis: [{
            show: false,
            type: 'value',
            min: function(value){
                return 0.9*value.min
            },
            max: function(value){
                return 1.1*value.min
            }
        }, {
            show: false,
            type: 'value',
            min: function(value){
                return 0.9*value.min
            },
            max: function(value){
                return 1.1*value.min
            }
        }
        ],
        series: [{
            name: '实际值',
            type: 'line',
            data: null,
            showSymbol: false,
            yAxisIndex: 0,
            lineStyle: {
                normal: {
                    color: '#ea6e0c',
                    width: 1
                }
            }
        }, {
            name: '预测值',
            type: 'line',
            data: null,
            showSymbol: false,
            yAxisIndex: 1,
            lineStyle: {
                normal: {
                    color: '#c1f3ec',
                    width: 1
                }
            }
        }
        ]
    }

    this.option.series[0].data = this.render_values
}

AiTrain.prototype.train = function () {
    var self = this
    console.log("Train id: "+self.id)

    $.ajax({
        url: "/ai/train?" + self.id,
        type: 'POST',
        data: JSON.stringify(self.parameters),
        contentType: 'application/json',
        success: function (data) {
            setTimeout(self._fetchHistory, 100, self)
        }
    })
}

AiTrain.prototype.stop = function () {
    var self = this

    $.ajax({
        url: "/ai/cancel?" + self.id,
        type: 'GET',
        success: function (data) {
            console.log("Cancel:" + data)
        }
    })
}

AiTrain.prototype.show = function (start, end) {
    this.option.dataZoom[0].start = start || 70
    this.option.dataZoom[0].end = end || 100
    this.chart.setOption(this.option)
}

AiTrain.prototype.appendChart = function(start, end){
    console.log(" append a new chart ")
}

AiTrain.prototype._fetchHistory = function (self) {
    $.ajax({
        url: "/ai/history?" + self.id,
        type: 'GET',
        dataType: "json",
        success: function (data) {
            if (data.predict) {
                var values = data.predict
                var start = self.train_values.length - values.length
                self.option.series[1].data = self.render_values.slice(start).map(function (e, i) {
                    return [e[0], values[i]]
                })
                self.show()
            }

            if (data.status.indexOf('Finished') < 0) {
                setTimeout(self._fetchHistory, 100, self)
            } else {
                console.log("Finished")
            }
        }
    })
}

AI = {
    chart: null,
    train: null,
    parseCMD: function(cmd){
        console.log(cmd)
        if(cmd.indexOf('set') == 0){

        } else if(cmd.indexOf('type') == 0){
            if(cmd.indexOf('sin') > 0){
                var values = AI.makeValues(AI.sin, 4000)

                AI.train = new AiTrain('sin_10001', AI.chart, values)
                AI.train.show()
            }
        } else if(cmd.indexof('json') == 0){
            var command = JSON.parse(cmd)
        }
    },
    sin: function(x){
       return Math.sin((x%360)*2*Math.PI/360)
    },
    makeValues: function(func, len){
        var values = []

        for(var i=0; i<len; i++){
            values.push(func(i))
        }

        return values
    },
    startTrain: function(){
        AI.train.train()
    },
    stopTrain: function(){
        AI.train.stop()
    },
    preview: function(){
        $.ajax({
            url: "/ai/mock/preview",
            success: function(result){
                AI.train = new AiTrain(result.name, AI.chart, result.values)
                AI.train.show(1, 100)
            }
        })
    },
    execute: function(command) {
        eval(command)
    }

}
