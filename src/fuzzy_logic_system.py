# 模糊逻辑系统模块 - 用于EEHFR协议
# 参考文献：
# [1] Nayak, P., & Vathasavai, B. (2017). Energy efficient clustering algorithm for multi-hop wireless sensor network using type-2 fuzzy logic.
# [2] Balakrishnan, B., & Balachandran, S. (2017). FLECH: fuzzy logic based energy efficient clustering hierarchy for nonuniform wireless sensor networks.
# [3] Logambigai, R., & Kannan, A. (2018). Fuzzy logic based unequal clustering for wireless sensor networks.

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

class FuzzyLogicSystem:
    """完整的模糊逻辑系统，用于WSN中的决策优化"""
    
    def __init__(self):
        # 创建模糊逻辑控制系统
        self.setup_fuzzy_system()
        
    def setup_fuzzy_system(self):
        """设置模糊逻辑系统的输入、输出和规则"""
        # 创建模糊变量 - 输入
        self.residual_energy = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'residual_energy')
        self.node_centrality = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'node_centrality')
        self.node_degree = ctrl.Antecedent(np.arange(0, 20.1, 0.1), 'node_degree')
        self.distance_to_bs = ctrl.Antecedent(np.arange(0, 300.1, 0.1), 'distance_to_bs')
        self.link_quality = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'link_quality')
        
        # 创建模糊变量 - 输出
        self.cluster_head_chance = ctrl.Consequent(np.arange(0, 1.01, 0.01), 'cluster_head_chance')
        self.next_hop_suitability = ctrl.Consequent(np.arange(0, 1.01, 0.01), 'next_hop_suitability')
        
        # 定义模糊集 - 剩余能量
        self.residual_energy['low'] = fuzz.trimf(self.residual_energy.universe, [0, 0, 0.4])
        self.residual_energy['medium'] = fuzz.trimf(self.residual_energy.universe, [0.2, 0.5, 0.8])
        self.residual_energy['high'] = fuzz.trimf(self.residual_energy.universe, [0.6, 1, 1])
        
        # 定义模糊集 - 节点中心性
        self.node_centrality['low'] = fuzz.trimf(self.node_centrality.universe, [0, 0, 0.4])
        self.node_centrality['medium'] = fuzz.trimf(self.node_centrality.universe, [0.2, 0.5, 0.8])
        self.node_centrality['high'] = fuzz.trimf(self.node_centrality.universe, [0.6, 1, 1])
        
        # 定义模糊集 - 节点度（邻居数量）
        self.node_degree['few'] = fuzz.trimf(self.node_degree.universe, [0, 0, 6])
        self.node_degree['moderate'] = fuzz.trimf(self.node_degree.universe, [4, 8, 12])
        self.node_degree['many'] = fuzz.trimf(self.node_degree.universe, [10, 15, 20])
        
        # 定义模糊集 - 到基站的距离
        self.distance_to_bs['close'] = fuzz.trimf(self.distance_to_bs.universe, [0, 0, 100])
        self.distance_to_bs['medium'] = fuzz.trimf(self.distance_to_bs.universe, [50, 150, 250])
        self.distance_to_bs['far'] = fuzz.trimf(self.distance_to_bs.universe, [200, 300, 300])
        
        # 定义模糊集 - 链路质量
        self.link_quality['poor'] = fuzz.trimf(self.link_quality.universe, [0, 0, 0.4])
        self.link_quality['average'] = fuzz.trimf(self.link_quality.universe, [0.3, 0.6, 0.8])
        self.link_quality['good'] = fuzz.trimf(self.link_quality.universe, [0.7, 1, 1])
        
        # 定义模糊集 - 簇头机会
        self.cluster_head_chance['very_low'] = fuzz.trimf(self.cluster_head_chance.universe, [0, 0, 0.25])
        self.cluster_head_chance['low'] = fuzz.trimf(self.cluster_head_chance.universe, [0.1, 0.3, 0.5])
        self.cluster_head_chance['medium'] = fuzz.trimf(self.cluster_head_chance.universe, [0.4, 0.6, 0.8])
        self.cluster_head_chance['high'] = fuzz.trimf(self.cluster_head_chance.universe, [0.7, 0.85, 1])
        self.cluster_head_chance['very_high'] = fuzz.trimf(self.cluster_head_chance.universe, [0.85, 1, 1])
        
        # 定义模糊集 - 下一跳适合度
        self.next_hop_suitability['unsuitable'] = fuzz.trimf(self.next_hop_suitability.universe, [0, 0, 0.3])
        self.next_hop_suitability['less_suitable'] = fuzz.trimf(self.next_hop_suitability.universe, [0.2, 0.4, 0.6])
        self.next_hop_suitability['suitable'] = fuzz.trimf(self.next_hop_suitability.universe, [0.5, 0.7, 0.9])
        self.next_hop_suitability['very_suitable'] = fuzz.trimf(self.next_hop_suitability.universe, [0.8, 1, 1])
        
        # 定义模糊规则 - 簇头选择规则
        self.ch_rules = [
            # 规则1：如果能量高且中心性高，则簇头机会很高
            ctrl.Rule(self.residual_energy['high'] & self.node_centrality['high'], 
                      self.cluster_head_chance['very_high']),
            
            # 规则2：如果能量高且中心性中等，则簇头机会高
            ctrl.Rule(self.residual_energy['high'] & self.node_centrality['medium'], 
                      self.cluster_head_chance['high']),
            
            # 规则3：如果能量中等且中心性高，则簇头机会高
            ctrl.Rule(self.residual_energy['medium'] & self.node_centrality['high'], 
                      self.cluster_head_chance['high']),
            
            # 规则4：如果能量中等且中心性中等，则簇头机会中等
            ctrl.Rule(self.residual_energy['medium'] & self.node_centrality['medium'], 
                      self.cluster_head_chance['medium']),
            
            # 规则5：如果能量低，则簇头机会很低
            ctrl.Rule(self.residual_energy['low'], self.cluster_head_chance['very_low']),
            
            # 规则6：如果中心性低，则簇头机会低
            ctrl.Rule(self.node_centrality['low'], self.cluster_head_chance['low']),
            
            # 规则7：如果能量高且邻居多，则簇头机会很高
            ctrl.Rule(self.residual_energy['high'] & self.node_degree['many'], 
                      self.cluster_head_chance['very_high']),
            
            # 规则8：如果能量中等且邻居适中，则簇头机会中等
            ctrl.Rule(self.residual_energy['medium'] & self.node_degree['moderate'], 
                      self.cluster_head_chance['medium']),
            
            # 规则9：如果到基站距离近且能量高，则簇头机会高
            ctrl.Rule(self.distance_to_bs['close'] & self.residual_energy['high'], 
                      self.cluster_head_chance['high']),
            
            # 规则10：如果到基站距离远且能量低，则簇头机会很低
            ctrl.Rule(self.distance_to_bs['far'] & self.residual_energy['low'],
                      self.cluster_head_chance['very_low']),

            # 新增规则：结合链路质量
            # 规则11: 如果链路质量好且能量高，则簇头机会非常高
            ctrl.Rule(self.link_quality['good'] & self.residual_energy['high'],
                      self.cluster_head_chance['very_high']),
            
            # 规则12: 如果链路质量好但能量中等，则簇头机会高
            ctrl.Rule(self.link_quality['good'] & self.residual_energy['medium'],
                      self.cluster_head_chance['high']),

            # 规则13: 如果链路质量差，则显著降低簇头机会
            ctrl.Rule(self.link_quality['poor'], self.cluster_head_chance['very_low']),

            # 规则14: 如果链路质量好，且邻居多，则是一个非常理想的簇头
            ctrl.Rule(self.link_quality['good'] & self.node_degree['many'],
                      self.cluster_head_chance['very_high'])
        ]
        
        # 定义模糊规则 - 下一跳选择规则
        self.nh_rules = [
            # 规则1：如果能量高且链路质量好且距离基站近，则非常适合作为下一跳
            ctrl.Rule(self.residual_energy['high'] & self.link_quality['good'] & 
                      self.distance_to_bs['close'], self.next_hop_suitability['very_suitable']),
            
            # 规则2：如果能量高且链路质量好，则适合作为下一跳
            ctrl.Rule(self.residual_energy['high'] & self.link_quality['good'], 
                      self.next_hop_suitability['suitable']),
            
            # 规则3：如果能量中等且链路质量好，则适合作为下一跳
            ctrl.Rule(self.residual_energy['medium'] & self.link_quality['good'], 
                      self.next_hop_suitability['suitable']),
            
            # 规则4：如果能量低，则不适合作为下一跳
            ctrl.Rule(self.residual_energy['low'], self.next_hop_suitability['unsuitable']),
            
            # 规则5：如果链路质量差，则不太适合作为下一跳
            ctrl.Rule(self.link_quality['poor'], self.next_hop_suitability['less_suitable']),
            
            # 规则6：如果能量中等且链路质量一般，则不太适合作为下一跳
            ctrl.Rule(self.residual_energy['medium'] & self.link_quality['average'], 
                      self.next_hop_suitability['less_suitable']),
            
            # 规则7：如果距离基站远且能量低，则不适合作为下一跳
            ctrl.Rule(self.distance_to_bs['far'] & self.residual_energy['low'], 
                      self.next_hop_suitability['unsuitable']),
            
            # 规则8：如果距离基站近且链路质量好，则非常适合作为下一跳
            ctrl.Rule(self.distance_to_bs['close'] & self.link_quality['good'], 
                      self.next_hop_suitability['very_suitable'])
        ]
        
        # 创建控制系统
        self.ch_ctrl = ctrl.ControlSystem(self.ch_rules)
        self.nh_ctrl = ctrl.ControlSystem(self.nh_rules)
        
        # 创建控制系统模拟器
        self.ch_simulator = ctrl.ControlSystemSimulation(self.ch_ctrl)
        self.nh_simulator = ctrl.ControlSystemSimulation(self.nh_ctrl)
    
    def calculate_cluster_head_chance(self, residual_energy, node_centrality, node_degree, distance_to_bs, link_quality):
        """计算节点成为簇头的机会
        
        参数:
            residual_energy (float): 节点剩余能量比例 [0,1]
            node_centrality (float): 节点中心性 [0,1]
            node_degree (int): 节点度（邻居数量）
            distance_to_bs (float): 到基站的距离
            link_quality (float): 链路质量指数 [0,1]
            
        返回:
            float: 节点成为簇头的机会 [0,1]
        """
        # 设置输入值
        self.ch_simulator.input['residual_energy'] = residual_energy
        self.ch_simulator.input['node_centrality'] = node_centrality
        self.ch_simulator.input['node_degree'] = min(node_degree, 20)  # 限制在定义范围内
        self.ch_simulator.input['distance_to_bs'] = min(distance_to_bs, 300)  # 限制在定义范围内
        self.ch_simulator.input['link_quality'] = link_quality
        
        # 计算
        try:
            self.ch_simulator.compute()
            return self.ch_simulator.output['cluster_head_chance']
        except:
            # 如果计算失败，使用加权平均值作为备选方法
            weighted_sum = (residual_energy * 0.4 + 
                           node_centrality * 0.3 + 
                           min(node_degree / 20, 1) * 0.2 + 
                           (1 - min(distance_to_bs / 300, 1)) * 0.1)
            return weighted_sum
    
    def calculate_next_hop_suitability(self, residual_energy, link_quality, distance_to_bs):
        """计算节点作为下一跳的适合度
        
        参数:
            residual_energy (float): 节点剩余能量比例 [0,1]
            link_quality (float): 链路质量 [0,1]
            distance_to_bs (float): 到基站的距离
            
        返回:
            float: 节点作为下一跳的适合度 [0,1]
        """
        # 设置输入值
        self.nh_simulator.input['residual_energy'] = residual_energy
        self.nh_simulator.input['link_quality'] = link_quality
        self.nh_simulator.input['distance_to_bs'] = min(distance_to_bs, 300)  # 限制在定义范围内
        
        # 计算
        try:
            self.nh_simulator.compute()
            return self.nh_simulator.output['next_hop_suitability']
        except:
            # 如果计算失败，使用加权平均值作为备选方法
            weighted_sum = (residual_energy * 0.4 + 
                           link_quality * 0.4 + 
                           (1 - min(distance_to_bs / 300, 1)) * 0.2)
            return weighted_sum

    def visualize_membership_functions(self):
        """可视化模糊集的隶属度函数"""
        import matplotlib.pyplot as plt
        
        # 设置风格和字体
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams.update({
            'font.size': 12,
            'axes.labelsize': 14,
            'axes.titlesize': 16,
            'xtick.labelsize': 12,
            'ytick.labelsize': 12,
            'legend.fontsize': 12,
            'figure.titlesize': 18
        })
        
        # 创建一个大的图形，包含所有隶属度函数
        fig = plt.figure(figsize=(15, 18), dpi=100)
        fig.suptitle('Fuzzy Logic Membership Functions', fontsize=22, fontweight='bold', y=0.98)
        fig.set_facecolor('#f8f9fa')
        
        # 设置颜色方案
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
        
        # 创建子图布局
        gs = fig.add_gridspec(4, 2, hspace=0.4, wspace=0.3)
        
        # 自定义可视化输入变量 - 剩余能量
        ax1 = fig.add_subplot(gs[0, 0])
        x = np.arange(0, 1.01, 0.01)
        for i, term in enumerate(['low', 'medium', 'high']):
            ax1.plot(x, self.residual_energy[term].mf, 
                    linewidth=2.5, label=term.capitalize(), color=colors[i])
        ax1.set_title('Residual Energy', fontweight='bold', pad=10)
        ax1.set_xlabel('Energy Ratio [0-1]')
        ax1.set_ylabel('Membership Degree')
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.legend(loc='best')
        ax1.set_ylim([0, 1.1])
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # 自定义可视化输入变量 - 节点中心性
        ax2 = fig.add_subplot(gs[0, 1])
        for i, term in enumerate(['low', 'medium', 'high']):
            ax2.plot(x, self.node_centrality[term].mf, 
                    linewidth=2.5, label=term.capitalize(), color=colors[i])
        ax2.set_title('Node Centrality', fontweight='bold', pad=10)
        ax2.set_xlabel('Centrality Value [0-1]')
        ax2.set_ylabel('Membership Degree')
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.legend(loc='best')
        ax2.set_ylim([0, 1.1])
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        # 自定义可视化输入变量 - 节点度
        ax3 = fig.add_subplot(gs[1, 0])
        x_degree = np.arange(0, 20.1, 0.1)
        for i, term in enumerate(['few', 'moderate', 'many']):
            ax3.plot(x_degree, self.node_degree[term].mf, 
                    linewidth=2.5, label=term.capitalize(), color=colors[i])
        ax3.set_title('Node Degree', fontweight='bold', pad=10)
        ax3.set_xlabel('Number of Neighbors')
        ax3.set_ylabel('Membership Degree')
        ax3.grid(True, linestyle='--', alpha=0.7)
        ax3.legend(loc='best')
        ax3.set_ylim([0, 1.1])
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        
        # 自定义可视化输入变量 - 到基站的距离
        ax4 = fig.add_subplot(gs[1, 1])
        x_dist = np.arange(0, 300.1, 0.1)
        for i, term in enumerate(['close', 'medium', 'far']):
            ax4.plot(x_dist, self.distance_to_bs[term].mf, 
                    linewidth=2.5, label=term.capitalize(), color=colors[i])
        ax4.set_title('Distance to Base Station', fontweight='bold', pad=10)
        ax4.set_xlabel('Distance (m)')
        ax4.set_ylabel('Membership Degree')
        ax4.grid(True, linestyle='--', alpha=0.7)
        ax4.legend(loc='best')
        ax4.set_ylim([0, 1.1])
        ax4.spines['top'].set_visible(False)
        ax4.spines['right'].set_visible(False)
        
        # 自定义可视化输入变量 - 链路质量
        ax5 = fig.add_subplot(gs[2, 0])
        for i, term in enumerate(['poor', 'average', 'good']):
            ax5.plot(x, self.link_quality[term].mf, 
                    linewidth=2.5, label=term.capitalize(), color=colors[i])
        ax5.set_title('Link Quality', fontweight='bold', pad=10)
        ax5.set_xlabel('Quality Value [0-1]')
        ax5.set_ylabel('Membership Degree')
        ax5.grid(True, linestyle='--', alpha=0.7)
        ax5.legend(loc='best')
        ax5.set_ylim([0, 1.1])
        ax5.spines['top'].set_visible(False)
        ax5.spines['right'].set_visible(False)
        
        # 自定义可视化输出变量 - 簇头机会
        ax6 = fig.add_subplot(gs[2, 1])
        for i, term in enumerate(['very_low', 'low', 'medium', 'high', 'very_high']):
            ax6.plot(x, self.cluster_head_chance[term].mf, 
                    linewidth=2.5, label=' '.join(term.split('_')).capitalize(), color=colors[i % len(colors)])
        ax6.set_title('Cluster Head Chance', fontweight='bold', pad=10)
        ax6.set_xlabel('Chance Value [0-1]')
        ax6.set_ylabel('Membership Degree')
        ax6.grid(True, linestyle='--', alpha=0.7)
        ax6.legend(loc='best')
        ax6.set_ylim([0, 1.1])
        ax6.spines['top'].set_visible(False)
        ax6.spines['right'].set_visible(False)
        
        # 自定义可视化输出变量 - 下一跳适合度
        ax7 = fig.add_subplot(gs[3, 0])
        for i, term in enumerate(['unsuitable', 'less_suitable', 'suitable', 'very_suitable']):
            ax7.plot(x, self.next_hop_suitability[term].mf, 
                    linewidth=2.5, label=' '.join(term.split('_')).capitalize(), color=colors[i % len(colors)])
        ax7.set_title('Next Hop Suitability', fontweight='bold', pad=10)
        ax7.set_xlabel('Suitability Value [0-1]')
        ax7.set_ylabel('Membership Degree')
        ax7.grid(True, linestyle='--', alpha=0.7)
        ax7.legend(loc='best')
        ax7.set_ylim([0, 1.1])
        ax7.spines['top'].set_visible(False)
        ax7.spines['right'].set_visible(False)
        
        # 添加说明文本
        description = (
            "Fuzzy Logic System for WSN Decision Making\n"
            "This visualization shows the membership functions used in the fuzzy inference system.\n"
            "These functions help translate crisp input values into fuzzy linguistic variables for decision making."
        )
        fig.text(0.5, 0.02, description, ha='center', fontsize=12, style='italic', 
                bbox=dict(facecolor='#f8f9fa', alpha=0.8, boxstyle='round,pad=0.5', edgecolor='#d5dbdb'))
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.94, bottom=0.08)
        plt.savefig('fuzzy_membership_functions.png', dpi=300, bbox_inches='tight')
        plt.show()

    def visualize_fuzzy_surface(self):
        """可视化模糊控制表面"""
        from mpl_toolkits.mplot3d import Axes3D
        import matplotlib.pyplot as plt
        
        # 设置风格和字体
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams.update({
            'font.size': 12,
            'axes.labelsize': 14,
            'axes.titlesize': 16,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 12,
            'figure.titlesize': 18
        })
        
        # 创建一个大的图形，包含所有控制表面
        fig = plt.figure(figsize=(16, 10), dpi=100)
        fig.suptitle('Fuzzy Logic Control Surfaces', fontsize=22, fontweight='bold', y=0.98)
        fig.set_facecolor('#f8f9fa')
        
        # 创建自定义的3D表面图 - 簇头选择（能量vs中心性）
        ax1 = fig.add_subplot(121, projection='3d')
        x_energy = np.arange(0, 1.01, 0.01)
        y_centrality = np.arange(0, 1.01, 0.01)
        X, Y = np.meshgrid(x_energy, y_centrality)
        Z = np.zeros_like(X)
        
        # 计算每个点的输出值
        for i in range(len(x_energy)):
            for j in range(len(y_centrality)):
                self.ch_simulator.input['residual_energy'] = x_energy[i]
                self.ch_simulator.input['node_centrality'] = y_centrality[j]
                self.ch_simulator.input['node_degree'] = 10  # 固定值
                self.ch_simulator.input['distance_to_bs'] = 150  # 固定值
                try:
                    self.ch_simulator.compute()
                    Z[j, i] = self.ch_simulator.output['cluster_head_chance']
                except:
                    Z[j, i] = 0.5  # 默认值
        
        # 绘制3D表面
        surf1 = ax1.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8, 
                               linewidth=0, antialiased=True, edgecolor='none')
        
        # 添加颜色条和标签
        cbar1 = fig.colorbar(surf1, ax=ax1, shrink=0.6, pad=0.1)
        cbar1.set_label('Cluster Head Chance')
        
        ax1.set_title('Cluster Head Selection Surface', fontweight='bold', pad=10)
        ax1.set_xlabel('Residual Energy')
        ax1.set_ylabel('Node Centrality')
        ax1.set_zlabel('CH Chance')
        ax1.view_init(elev=30, azim=45)  # 设置视角
        
        # 创建自定义的3D表面图 - 下一跳选择（能量vs链路质量）
        ax2 = fig.add_subplot(122, projection='3d')
        x_energy = np.arange(0, 1.01, 0.01)
        y_link = np.arange(0, 1.01, 0.01)
        X, Y = np.meshgrid(x_energy, y_link)
        Z = np.zeros_like(X)
        
        # 计算每个点的输出值
        for i in range(len(x_energy)):
            for j in range(len(y_link)):
                self.nh_simulator.input['residual_energy'] = x_energy[i]
                self.nh_simulator.input['link_quality'] = y_link[j]
                self.nh_simulator.input['distance_to_bs'] = 150  # 固定值
                try:
                    self.nh_simulator.compute()
                    Z[j, i] = self.nh_simulator.output['next_hop_suitability']
                except:
                    Z[j, i] = 0.5  # 默认值
        
        # 绘制3D表面
        surf2 = ax2.plot_surface(X, Y, Z, cmap='plasma', alpha=0.8, 
                               linewidth=0, antialiased=True, edgecolor='none')
        
        # 添加颜色条和标签
        cbar2 = fig.colorbar(surf2, ax=ax2, shrink=0.6, pad=0.1)
        cbar2.set_label('Next Hop Suitability')
        
        ax2.set_title('Next Hop Selection Surface', fontweight='bold', pad=10)
        ax2.set_xlabel('Residual Energy')
        ax2.set_ylabel('Link Quality')
        ax2.set_zlabel('NH Suitability')
        ax2.view_init(elev=30, azim=45)  # 设置视角
        
        # 添加说明文本
        description = (
            "Fuzzy Logic Control Surfaces for WSN Decision Making\n"
            "This visualization shows the membership functions used in the fuzzy inference system.\n"
            "These functions help translate crisp input values into fuzzy linguistic variables for decision making."
        )
        fig.text(0.5, 0.02, description, ha='center', fontsize=12, style='italic', 
                bbox=dict(facecolor='#f8f9fa', alpha=0.8, boxstyle='round,pad=0.5', edgecolor='#d5dbdb'))
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.92, bottom=0.1)
        plt.savefig('fuzzy_control_surfaces.png', dpi=300, bbox_inches='tight')
        plt.show()

# 测试代码
if __name__ == "__main__":
    # 创建模糊逻辑系统
    fls = FuzzyLogicSystem()
    
    # 测试簇头选择
    ch_chance = fls.calculate_cluster_head_chance(
        residual_energy=0.8,  # 高剩余能量
        node_centrality=0.7,  # 高中心性
        node_degree=12,       # 适中的邻居数量
        distance_to_bs=80     # 较近的基站距离
    )
    print(f"簇头选择机会: {ch_chance:.4f}")
    
    # 测试下一跳选择
    nh_suitability = fls.calculate_next_hop_suitability(
        residual_energy=0.6,  # 中等剩余能量
        link_quality=0.8,     # 良好的链路质量
        distance_to_bs=120    # 中等的基站距离
    )
    print(f"下一跳适合度: {nh_suitability:.4f}")
    
    # 可视化
    # fls.visualize_membership_functions()
    # fls.visualize_fuzzy_surface()
