Vue.component("vue-pagination-component", {
    props: ["pages"],
    template: ``,
    methods: {
        flipPage: function(e){
            var index = e.target.text
            this.$emit('refresh', index)
        },
        upPage: function(){
            this.$emit('refresh', this.pages.curPnum -1)
        },
        downPage: function(){
            this.$emit('refresh', this.pages.curPnum + 1)
        },
        choosePage: function(){
            var index = $('#selectPage').val()
            this.$emit('refresh', index)
        }
    }

})