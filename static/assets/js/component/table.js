Vue.component('vue-table-component', {
    props: ["records", "columns", "id"],
    template:`
                <table width="100%" class="am-table am-table-compact am-table-striped tpl-table-black " :id="id">
                <thead>
                    <tr>
                        <th v-for="item in columns">{{item[0]}}</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-bind:class="[index%2 ? 'gradeX' : 'even gradeC']" v-for="(record, index) in records">
                        <td v-for="value in record">{{value}}</td>
                        <td>
                            <div class="tpl-table-black-operation">
                                <a href="javascript:;">
                                    <i class="am-icon-pencil"></i> 编辑
                                </a>
                                <a href="javascript:;" class="tpl-table-black-operation-del">
                                    <i class="am-icon-trash"></i> 删除
                                </a>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>`,
    methods: {
        operate: function(e){
            this.$emit('operation', e.target)
        }
    }
})