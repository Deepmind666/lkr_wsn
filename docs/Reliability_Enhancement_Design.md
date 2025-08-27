# 可靠性增强模块设计文档 (Reliability Enhancement Design)

## 1. 模块目标

本模块旨在为`Enhanced EEHFR`协议引入**可靠性感知**能力。核心是设计并实现一个`NodeStateManager`类，用于跟踪、计算和提供每个节点的**链路质量指数(Link Quality Indicator, LQI)**。这将作为增强模糊逻辑簇头选择机制的关键输入，使协议能够优先选择通信链路更稳定的节点作为簇头，从而提高网络的数据投递率和整体能效。

## 2. 核心数据结构

### `LinkQualityRecord`

用于记录与单个邻居节点的通信质量。

```python
from dataclasses import dataclass

@dataclass
class LinkQualityRecord:
    """记录与单个邻居的链路质量历史"""
    neighbor_id: int
    rssi_history: list[float]
    pdr_history: list[float]
    last_updated_round: int
```

### `NodeStateManager`

管理网络中所有节点的状态。它将是协议中的一个核心组件。

```python
from collections import deque

class NodeStateManager:
    """管理全网节点的动态状态，特别是链路质量。"""
    def __init__(self, num_nodes: int, history_window: int = 50):
        self.num_nodes = num_nodes
        self.history_window = history_window  # 用于计算滑动平均的窗口大小
        # 存储结构: self.node_states[node_id][neighbor_id] -> LinkQualityRecord
        self.node_states: dict[int, dict[int, LinkQualityRecord]] = {i: {} for i in range(num_nodes)}
        self.lqi_cache: dict[int, tuple[float, int]] = {}  # 缓存: {node_id: (lqi, last_calculated_round)}

    def update_link_quality(self, sender_id: int, receiver_id: int, rssi: float, is_success: bool, current_round: int):
        """
        更新两个节点间的双向链路质量记录。
        """
        self._update_single_link(sender_id, receiver_id, rssi, is_success, current_round)
        self._update_single_link(receiver_id, sender_id, rssi, is_success, current_round)

    def _update_single_link(self, source_id: int, dest_id: int, rssi: float, is_success: bool, current_round: int):
        """内部辅助函数，更新单向链路记录。"""
        if dest_id not in self.node_states[source_id]:
            self.node_states[source_id][dest_id] = LinkQualityRecord(
                neighbor_id=dest_id,
                rssi_history=deque(maxlen=self.history_window),
                pdr_history=deque(maxlen=self.history_window),
                last_updated_round=current_round
            )
        
        record = self.node_states[source_id][dest_id]
        record.rssi_history.append(rssi)
        record.pdr_history.append(1.0 if is_success else 0.0)
        record.last_updated_round = current_round

    def get_lqi(self, node_id: int, current_round: int, w_pdr: float = 0.6, w_rssi: float = 0.4) -> float:
        """
        计算并获取一个节点的综合LQI。
        使用缓存避免在同一轮内重复计算。
        """
        if node_id in self.lqi_cache and self.lqi_cache[node_id][1] == current_round:
            return self.lqi_cache[node_id][0]

        neighbor_links = self.node_states.get(node_id, {})
        if not neighbor_links:
            return 0.0  # 如果没有邻居，LQI为0

        # 计算所有邻居链路的平均PDR和RSSI
        total_pdr = 0.0
        total_rssi = 0.0
        link_count = 0
        for neighbor_id, record in neighbor_links.items():
            if record.pdr_history:
                total_pdr += sum(record.pdr_history) / len(record.pdr_history)
                total_rssi += sum(record.rssi_history) / len(record.rssi_history)
                link_count += 1
        
        if link_count == 0:
            return 0.0

        avg_pdr = total_pdr / link_count
        avg_rssi = total_rssi / link_count
        
        # 归一化RSSI (假设RSSI范围在-100dBm到-30dBm之间)
        normalized_rssi = (avg_rssi - (-100)) / ((-30) - (-100))
        normalized_rssi = max(0.0, min(1.0, normalized_rssi)) # 确保在[0,1]范围内

        # 计算加权LQI
        lqi = w_pdr * avg_pdr + w_rssi * normalized_rssi
        
        self.lqi_cache[node_id] = (lqi, current_round)
        return lqi

    def get_network_lqi_stats(self, current_round: int) -> dict:
        """获取全网的LQI统计信息 (均值、方差等)"""
        all_lqi = [self.get_lqi(i, current_round) for i in range(self.num_nodes)]
        if not all_lqi:
            return {'mean': 0, 'std_dev': 0, 'min': 0, 'max': 0}
            
        mean_lqi = sum(all_lqi) / len(all_lqi)
        std_dev_lqi = (sum([(x - mean_lqi) ** 2 for x in all_lqi]) / len(all_lqi)) ** 0.5
        return {
            'mean': mean_lqi,
            'std_dev': std_dev_lqi,
            'min': min(all_lqi),
            'max': max(all_lqi)
        }

```

## 3. LQI计算方法

节点的LQI是一个0到1之间的归一化数值，值越高代表其平均链路质量越好。它由两部分加权组成：

**计算公式:**

`LQI(node_i) = w_pdr * avg_PDR(node_i) + w_rssi * avg_RSSI_normalized(node_i)`

-   **`avg_PDR`**: 节点`i`与其所有邻居的**滑动窗口平均PDR**。这反映了近期通信的成功率。
-   **`avg_RSSI_normalized`**: 节点`i`与其所有邻居的**滑动窗口平均RSSI**，并将其归一化到`[0, 1]`区间。这反映了信号强度。
-   **`w_pdr`, `w_rssi`**: 权重系数，例如 `w_pdr=0.6`, `w_rssi=0.4`，表示我们更看重直接反映数据送达情况的PDR。

## 4. 与主协议的集成方案

1.  在`IntegratedEnhancedEEHFRProtocol`的`__init__`中，实例化一个`NodeStateManager`对象。
2.  在仿真循环的每一次数据传输后，调用`state_manager.update_link_quality()`方法来更新相关节点的链路记录。
3.  在每一轮簇头选举开始前，为每个节点调用`state_manager.get_lqi()`来获取其最新的LQI值。
4.  将计算出的LQI作为第四个输入变量，传递给模糊逻辑引擎。
5.  修改模糊逻辑规则库，增加处理LQI的规则，例如：
    > "IF LQI is **High** AND ResidualEnergy is **High** THEN ChanceToBeCH is **VeryHigh**"

## 5. 下一步实施计划

1.  **模式切换**: 请求切换到`code`模式。
2.  **创建文件**: 在`src/`目录下创建`node_state_manager.py`文件。
3.  **实现类**: 将本设计文档中定义的`LinkQualityRecord`和`NodeStateManager`类实现到文件中。
4.  **集成代码**: 修改`integrated_enhanced_eehfr.py`，完成`NodeStateManager`的实例化和调用。
5.  **修改模糊逻辑**: 调整`fuzzy_logic_system.py`（如果存在）或相关代码，以支持新的LQI输入。
6.  **测试**: 运行`comprehensive_benchmark.py`，对比加入LQI前后的性能差异。

这个设计文档为下一步的编码工作提供了清晰的指引。