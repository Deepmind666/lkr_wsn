# 混合元启发式算法模块 - 用于EEHFR协议
# 参考文献：
# [4] Kuila, P., & Jana, P. K. (2014). Energy efficient clustering and routing algorithms for wireless sensor networks: Particle swarm optimization approach.
# [5] Elhabyan, R. S., & Yagoub, M. C. (2015). Two-tier particle swarm optimization protocol for clustering and routing in wireless sensor network.
# [6] Singh, B., & Lobiyal, D. K. (2012). A novel energy-aware cluster head selection based on particle swarm optimization for wireless sensor networks.
# [7] Gupta, G. P., & Jha, S. (2018). Integrated clustering and routing protocol for wireless sensor networks using Cuckoo and harmony search based metaheuristic techniques.

import numpy as np
import random
import math

class HybridMetaheuristic:
    """混合元启发式算法，结合PSO和ACO优化WSN路由"""
    
    def __init__(self, network_size=100, area_size=200, base_station_pos=(100, 100)):
        self.network_size = network_size
        self.area_size = area_size
        self.base_station = base_station_pos
        
        # PSO参数
        self.pso_population_size = 20
        self.pso_max_iterations = 50
        self.w = 0.7  # 惯性权重
        self.c1 = 1.5  # 认知参数
        self.c2 = 1.5  # 社会参数
        
        # ACO参数
        self.aco_ants = 20
        self.aco_iterations = 30
        self.alpha = 1.0  # 信息素重要性
        self.beta = 2.0   # 启发式信息重要性
        self.rho = 0.1    # 信息素蒸发率
        self.Q = 100      # 信息素强度
        
        # 混合算法参数
        self.hybrid_iterations = 10
        self.pso_weight = 0.5  # PSO结果权重
        self.aco_weight = 0.5  # ACO结果权重
    
    def optimize_clustering(self, nodes, n_clusters):
        """使用PSO优化网络分簇
        
        参数:
            nodes: 网络节点列表
            n_clusters: 期望的簇数量
            
        返回:
            最优的簇头节点列表
        """
        alive_nodes = [node for node in nodes if node.is_alive]
        if len(alive_nodes) <= n_clusters:
            return alive_nodes  # 如果活跃节点数少于簇数，所有节点都是簇头
        
        # 初始化PSO粒子群
        particles = []
        velocities = []
        personal_best_positions = []
        personal_best_scores = []
        
        # 全局最优解
        global_best_position = None
        global_best_score = -float('inf')
        
        # 初始化粒子位置和速度
        for _ in range(self.pso_population_size):
            # 随机选择n_clusters个节点作为簇头
            particle = random.sample(range(len(alive_nodes)), n_clusters)
            particles.append(particle)
            
            # 初始化速度为0
            velocity = [0] * n_clusters
            velocities.append(velocity)
            
            # 评估粒子适应度
            score = self._evaluate_clustering(particle, alive_nodes)
            
            # 更新个体最优
            personal_best_positions.append(particle.copy())
            personal_best_scores.append(score)
            
            # 更新全局最优
            if score > global_best_score:
                global_best_score = score
                global_best_position = particle.copy()
        
        # PSO迭代优化
        for _ in range(self.pso_max_iterations):
            for i in range(self.pso_population_size):
                # 更新速度和位置
                for j in range(n_clusters):
                    # 更新速度
                    r1, r2 = random.random(), random.random()
                    velocities[i][j] = (self.w * velocities[i][j] + 
                                       self.c1 * r1 * (personal_best_positions[i][j] - particles[i][j]) + 
                                       self.c2 * r2 * (global_best_position[j] - particles[i][j]))
                    
                    # 更新位置（离散PSO）
                    new_pos = particles[i][j] + int(velocities[i][j])
                    new_pos = max(0, min(new_pos, len(alive_nodes) - 1))
                    particles[i][j] = new_pos
                
                # 确保没有重复的簇头
                particles[i] = list(set(particles[i]))
                while len(particles[i]) < n_clusters:
                    new_node = random.randint(0, len(alive_nodes) - 1)
                    if new_node not in particles[i]:
                        particles[i].append(new_node)
                
                # 评估新位置
                score = self._evaluate_clustering(particles[i], alive_nodes)
                
                # 更新个体最优
                if score > personal_best_scores[i]:
                    personal_best_scores[i] = score
                    personal_best_positions[i] = particles[i].copy()
                
                # 更新全局最优
                if score > global_best_score:
                    global_best_score = score
                    global_best_position = particles[i].copy()
        
        # 返回最优簇头
        return [alive_nodes[idx] for idx in global_best_position]
    
    def _evaluate_clustering(self, particle, nodes):
        """评估分簇方案的适应度
        
        参数:
            particle: 表示簇头的粒子
            nodes: 所有活跃节点
            
        返回:
            适应度得分
        """
        # 获取簇头节点
        cluster_heads = [nodes[idx] for idx in particle]
        
        # 计算每个节点到最近簇头的距离
        total_distance = 0
        for node in nodes:
            if node not in cluster_heads:
                min_distance = float('inf')
                for ch in cluster_heads:
                    distance = node.calculate_distance(ch)
                    if distance < min_distance:
                        min_distance = distance
                total_distance += min_distance
        
        # 计算簇头的平均能量
        avg_energy = sum(ch.energy for ch in cluster_heads) / len(cluster_heads)
        
        # 计算簇头的平均距离到基站
        avg_distance_to_bs = sum(ch.distance_to_bs for ch in cluster_heads) / len(cluster_heads)
        
        # 适应度函数：最小化节点到簇头的距离，最大化簇头能量，最小化簇头到基站的距离
        # 归一化各项指标
        norm_distance = 1 / (1 + total_distance / len(nodes))
        norm_energy = avg_energy / 2.0  # 假设初始能量为2.0J
        norm_bs_distance = 1 / (1 + avg_distance_to_bs / 300)  # 假设最大距离为300m
        
        # 综合适应度
        fitness = 0.4 * norm_distance + 0.4 * norm_energy + 0.2 * norm_bs_distance
        
        return fitness
    
    def optimize_routing(self, cluster_heads, base_station):
        """使用ACO优化簇头到基站的路由
        
        参数:
            cluster_heads: 簇头节点列表
            base_station: 基站节点
            
        返回:
            优化后的路由路径（每个簇头的下一跳）
        """
        n_ch = len(cluster_heads)
        if n_ch == 0:
            return {}
        
        # 如果只有一个簇头，直接连接到基站
        if n_ch == 1:
            return {cluster_heads[0].id: base_station}
        
        # 构建距离矩阵和信息素矩阵
        # 添加基站作为最后一个节点
        all_nodes = cluster_heads + [base_station]
        n_nodes = len(all_nodes)
        
        # 距离矩阵
        distances = np.zeros((n_nodes, n_nodes))
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i != j:
                    distances[i, j] = all_nodes[i].calculate_distance(all_nodes[j])
                else:
                    distances[i, j] = float('inf')  # 自己到自己的距离设为无穷大
        
        # 初始化信息素矩阵
        pheromones = np.ones((n_nodes, n_nodes)) * 0.1
        
        # 初始化最佳路径
        best_path = None
        best_path_length = float('inf')
        
        # ACO迭代优化
        for _ in range(self.aco_iterations):
            # 每只蚂蚁构建路径
            ant_paths = []
            ant_path_lengths = []
            
            for _ in range(self.aco_ants):
                # 随机选择起始簇头
                current = random.randint(0, n_ch - 1)
                path = [current]
                path_length = 0
                visited = [False] * n_nodes
                visited[current] = True
                
                # 构建路径直到所有簇头都被访问
                while len(path) < n_ch:
                    # 计算转移概率
                    probabilities = np.zeros(n_nodes)
                    for j in range(n_ch):
                        if not visited[j]:
                            # 计算启发式信息（距离的倒数）
                            eta = 1.0 / distances[current, j]
                            # 计算转移概率
                            probabilities[j] = (pheromones[current, j] ** self.alpha) * (eta ** self.beta)
                    
                    # 归一化概率
                    if np.sum(probabilities) > 0:
                        probabilities = probabilities / np.sum(probabilities)
                    
                    # 轮盘赌选择下一个节点
                    next_node = self._roulette_wheel_selection(probabilities)
                    
                    # 更新路径
                    path.append(next_node)
                    path_length += distances[current, next_node]
                    visited[next_node] = True
                    current = next_node
                
                # 连接到基站
                path.append(n_nodes - 1)  # 基站索引
                path_length += distances[current, n_nodes - 1]
                
                ant_paths.append(path)
                ant_path_lengths.append(path_length)
                
                # 更新最佳路径
                if path_length < best_path_length:
                    best_path_length = path_length
                    best_path = path.copy()
            
            # 更新信息素
            # 信息素蒸发
            pheromones = (1 - self.rho) * pheromones
            
            # 信息素沉积
            for i, path in enumerate(ant_paths):
                delta = self.Q / ant_path_lengths[i]
                for j in range(len(path) - 1):
                    pheromones[path[j], path[j+1]] += delta
        
        # 构建路由表（每个簇头的下一跳）
        routing_table = {}
        
        # 使用最佳路径构建路由表
        if best_path:
            # 将路径转换为路由表
            for i in range(len(best_path) - 1):
                ch_id = cluster_heads[best_path[i]].id
                next_hop = all_nodes[best_path[i+1]]
                routing_table[ch_id] = next_hop
        
        return routing_table
    
    def _roulette_wheel_selection(self, probabilities):
        """轮盘赌选择
        
        参数:
            probabilities: 概率数组
            
        返回:
            选中的索引
        """
        r = random.random()
        c = 0
        for i, p in enumerate(probabilities):
            c += p
            if r <= c:
                return i
        return len(probabilities) - 1
    
    def hybrid_optimize(self, nodes, n_clusters, base_station):
        """混合PSO和ACO进行分簇和路由优化
        
        参数:
            nodes: 网络节点列表
            n_clusters: 期望的簇数量
            base_station: 基站节点
            
        返回:
            (cluster_heads, routing_table): 簇头列表和路由表
        """
        best_cluster_heads = None
        best_routing_table = None
        best_score = -float('inf')
        
        for _ in range(self.hybrid_iterations):
            # PSO优化分簇
            cluster_heads = self.optimize_clustering(nodes, n_clusters)
            
            # ACO优化路由
            routing_table = self.optimize_routing(cluster_heads, base_station)
            
            # 评估整体解决方案
            score = self._evaluate_solution(cluster_heads, routing_table, nodes, base_station)
            
            # 更新最佳解决方案
            if score > best_score:
                best_score = score
                best_cluster_heads = cluster_heads.copy()
                best_routing_table = routing_table.copy()
        
        return best_cluster_heads, best_routing_table
    
    def _evaluate_solution(self, cluster_heads, routing_table, nodes, base_station):
        """评估整体解决方案的质量
        
        参数:
            cluster_heads: 簇头列表
            routing_table: 路由表
            nodes: 所有节点
            base_station: 基站节点
            
        返回:
            解决方案得分
        """
        # 评估分簇质量
        clustering_score = self._evaluate_clustering_solution(cluster_heads, nodes)
        
        # 评估路由质量
        routing_score = self._evaluate_routing_solution(routing_table, cluster_heads, base_station)
        
        # 综合得分
        return self.pso_weight * clustering_score + self.aco_weight * routing_score
    
    def _evaluate_clustering_solution(self, cluster_heads, nodes):
        """评估分簇解决方案"""
        # 计算每个节点到最近簇头的平均距离
        total_distance = 0
        for node in nodes:
            if node.is_alive and node not in cluster_heads:
                min_distance = float('inf')
                for ch in cluster_heads:
                    distance = node.calculate_distance(ch)
                    if distance < min_distance:
                        min_distance = distance
                total_distance += min_distance
        
        avg_distance = total_distance / max(1, len(nodes) - len(cluster_heads))
        
        # 计算簇头的平均能量
        avg_energy = sum(ch.energy for ch in cluster_heads) / max(1, len(cluster_heads))
        
        # 归一化
        norm_distance = 1 / (1 + avg_distance / 100)  # 假设最大距离为100m
        norm_energy = avg_energy / 2.0  # 假设初始能量为2.0J
        
        # 综合得分
        return 0.5 * norm_distance + 0.5 * norm_energy
    
    def _evaluate_routing_solution(self, routing_table, cluster_heads, base_station):
        """评估路由解决方案"""
        if not routing_table or not cluster_heads:
            return 0
        
        # 计算路由路径的总长度
        total_length = 0
        hop_count = 0
        
        for ch in cluster_heads:
            current = ch
            path_length = 0
            hops = 0
            
            # 跟踪路径直到到达基站或无法继续
            while current != base_station and current.id in routing_table:
                next_hop = routing_table[current.id]
                path_length += current.calculate_distance(next_hop)
                current = next_hop
                hops += 1
                
                # 防止循环
                if hops > len(cluster_heads):
                    break
            
            total_length += path_length
            hop_count += hops
        
        # 计算平均路径长度和跳数
        avg_length = total_length / len(cluster_heads)
        avg_hops = hop_count / len(cluster_heads)
        
        # 归一化
        norm_length = 1 / (1 + avg_length / 300)  # 假设最大长度为300m
        norm_hops = 1 / (1 + avg_hops / 10)  # 假设最大跳数为10
        
        # 综合得分
        return 0.7 * norm_length + 0.3 * norm_hops

# 测试代码
if __name__ == "__main":
    # 模拟节点类
    class TestNode:
        def __init__(self, id, x, y, energy=2.0):
            self.id = id
            self.x = x
            self.y = y
            self.energy = energy
            self.is_alive = True
            self.distance_to_bs = math.sqrt((x - 100)**2 + (y - 100)**2)
        
        def calculate_distance(self, node):
            return math.sqrt((self.x - node.x)**2 + (self.y - node.y)**2)
    
    # 创建测试节点
    test_nodes = []
    for i in range(100):
        x = random.uniform(0, 200)
        y = random.uniform(0, 200)
        energy = random.uniform(0.5, 2.0)
        test_nodes.append(TestNode(i, x, y, energy))
    
    # 创建基站
    base_station = TestNode(-1, 100, 100, float('inf'))
    
    # 创建混合元启发式算法实例
    hybrid = HybridMetaheuristic()
    
    # 测试分簇优化
    cluster_heads = hybrid.optimize_clustering(test_nodes, 5)
    print(f"优化后的簇头数量: {len(cluster_heads)}")
    print(f"簇头ID: {[ch.id for ch in cluster_heads]}")
    
    # 测试路由优化
    routing_table = hybrid.optimize_routing(cluster_heads, base_station)
    print(f"路由表大小: {len(routing_table)}")
    for ch_id, next_hop in routing_table.items():
        print(f"簇头 {ch_id} -> 下一跳 {next_hop.id}")
    
    # 测试混合优化
    best_chs, best_routes = hybrid.hybrid_optimize(test_nodes, 5, base_station)
    print(f"混合优化后的簇头数量: {len(best_chs)}")
    print(f"混合优化后的路由表大小: {len(best_routes)}")