# TermEd本身
## 你说得对，但是我就是这么处理瓶颈的
- 因为作品的某一个缺陷导致后续工作无法进行？重写呗（
## 虽然但是，不能让显示影响逻辑，就像不能让局部影响整体
- 所以list[list[list[str]]]本身就是不合逻辑的
- 争取将编辑、显示和插件解耦合开，然后由edcore粘在一起
- 所以这就是为什么Python是胶水语言（
- 事实上渲染复杂度再高也只有一屏，所以代码存储结构可以随便，只要不渲染复杂度与一屏之外的事物相关即可
- 一切事物的底层都很简洁，最复杂的那部分是外显的功能
- 这就是为什么自动折行很难写（
## 2024-8-22 写高亮之前还是有点犯怵，先写下思路
- 状态继承法，无论添加还是删除，只需要基于未修改的最后一行的尾状态分析
- 一直分析到未修改的一行，并且该行之前的尾状态未改变
### 不敢写，感觉工作量很大，完不成
- 凉拌
- 想想以前的伟大成就
- 为啥以前能完成那么多，是什么支撑着？
- 这不是兴趣爱好吗
- 去了
