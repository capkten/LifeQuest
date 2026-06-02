<template>
  <div class="todos-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">待办</h2>
        <span class="item-count">{{ currentList.length }} {{ activeTab === 'habits' ? '个习惯' : activeTab === 'tasks' ? '个任务' : '个目标' }}</span>
      </div>
      <button class="btn-create" @click="showCreateDialog = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建{{ activeTabSingular }}
      </button>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        <span class="tab-icon">
          <svg v-if="tab.id === 'habits'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
          <svg v-else-if="tab.id === 'tasks'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M9 11l3 3L22 4" />
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
          </svg>
          <svg v-else-if="tab.id === 'goals'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="6" />
            <circle cx="12" cy="12" r="2" />
          </svg>
        </span>
        <span class="tab-label">{{ tab.label }}</span>
        <span class="tab-count" :class="'tab-count--' + tab.id">{{ getCount(tab.id) }}</span>
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchAll">重试</button>
    </div>

    <div v-else-if="currentList.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M9 11l3 3L22 4" />
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
        </svg>
      </div>
      <h3 class="empty-title">暂无{{ activeTab === 'habits' ? '习惯' : activeTab === 'tasks' ? '任务' : '目标' }}</h3>
      <p class="empty-text">创建你的第一个{{ activeTabSingular }}，开始行动吧。</p>
      <button class="btn-create" @click="showCreateDialog = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        创建{{ activeTabSingular }}
      </button>
    </div>

    <div v-else class="todo-list">
      <!-- Habits List -->
      <template v-if="activeTab === 'habits'">
        <div
          v-for="habit in habits"
          :key="habit.id"
          class="todo-card"
        >
          <div class="todo-card-header">
            <div class="todo-card-main">
              <button
                class="complete-btn"
                :class="{ 'complete-btn--done': !habit.is_active }"
                :disabled="completingId === habit.id"
                @click="completeHabit(habit)"
                :aria-label="'Complete ' + habit.title"
              >
                <span v-if="completingId === habit.id" class="loading-spinner loading-spinner--sm"></span>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </button>
              <div class="todo-card-info">
                <h3 class="todo-card-title" :class="{ 'todo-card-title--done': !habit.is_active }">{{ habit.title }}</h3>
                <p v-if="habit.description" class="todo-card-desc">{{ habit.description }}</p>
              </div>
            </div>
            <div class="todo-card-actions">
              <div class="todo-card-meta">
                <span class="difficulty-badge" :class="'difficulty-badge--' + habit.difficulty">
                  {{ habit.difficulty === 'easy' ? '简单' : habit.difficulty === 'medium' ? '中等' : '困难' }}
                </span>
                <span class="frequency-badge" :class="'frequency-badge--' + habit.frequency">
                  {{ habit.frequency === 'daily' ? '每日' : habit.frequency === 'weekly' ? '每周' : '每月' }}
                </span>
              </div>
              <div class="action-buttons">
                <button class="action-btn action-btn--edit" @click="openEditDialog(habit, 'habits')" aria-label="编辑">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                </button>
                <button class="action-btn action-btn--delete" @click="openDeleteDialog(habit, 'habits')" aria-label="删除">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          <div class="todo-card-footer">
            <div class="todo-card-stats">
              <span class="stat-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                </svg>
                连续: {{ habit.streak }} (最佳: {{ habit.best_streak }})
              </span>
              <span class="stat-item stat-item--coins">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v12M6 12h12" />
                </svg>
                +{{ habit.coins_reward }}
              </span>
              <span class="stat-item stat-item--exp">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
                +{{ habit.exp_reward }} XP
              </span>
            </div>
          </div>
        </div>
      </template>

      <!-- Tasks List -->
      <template v-if="activeTab === 'tasks'">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="todo-card"
        >
          <div class="todo-card-header">
            <div class="todo-card-main">
              <button
                class="complete-btn"
                :class="{ 'complete-btn--done': task.status === 'completed' }"
                :disabled="task.status === 'completed' || completingId === task.id"
                @click="completeTask(task)"
                :aria-label="'Complete ' + task.title"
              >
                <span v-if="completingId === task.id" class="loading-spinner loading-spinner--sm"></span>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </button>
              <div class="todo-card-info">
                <h3 class="todo-card-title" :class="{ 'todo-card-title--done': task.status === 'completed' }">{{ task.title }}</h3>
                <p v-if="task.description" class="todo-card-desc">{{ task.description }}</p>
              </div>
            </div>
            <div class="todo-card-actions">
              <div class="todo-card-meta">
                <span class="difficulty-badge" :class="'difficulty-badge--' + task.difficulty">
                  {{ task.difficulty === 'easy' ? '简单' : task.difficulty === 'medium' ? '中等' : '困难' }}
                </span>
                <span class="status-badge" :class="'status-badge--' + task.status">
                  {{ formatStatus(task.status) }}
                </span>
              </div>
              <div class="action-buttons">
                <button class="action-btn action-btn--edit" @click="openEditDialog(task, 'tasks')" aria-label="编辑">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                </button>
                <button class="action-btn action-btn--delete" @click="openDeleteDialog(task, 'tasks')" aria-label="删除">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          <!-- Subtask Section for Tasks -->
          <div class="subtask-section">
            <button
              class="subtask-toggle-btn"
              @click="toggleTaskExpand(task)"
              :aria-expanded="expandedTaskId === task.id"
            >
              <svg
                class="subtask-toggle-icon"
                :class="{ 'subtask-toggle-icon--expanded': expandedTaskId === task.id }"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
              <span>子任务</span>
              <span v-if="taskSubtasks[task.id]" class="subtask-count-badge">
                {{ taskSubtasks[task.id].filter(s => s.is_completed).length }}/{{ taskSubtasks[task.id].length }}
              </span>
            </button>

            <div v-if="expandedTaskId === task.id" class="subtask-content">
              <div v-if="loadingSubtasks && !taskSubtasks[task.id]" class="subtask-loading">
                <span class="loading-spinner loading-spinner--sm"></span>
              </div>

              <template v-else>
                <div v-if="taskSubtasks[task.id] && taskSubtasks[task.id].length > 0" class="subtask-list">
                  <div
                    v-for="subtask in taskSubtasks[task.id]"
                    :key="subtask.id"
                    class="subtask-item"
                    :class="{ 'subtask-item--done': subtask.is_completed }"
                  >
                    <button
                      class="subtask-complete-btn"
                      :class="{ 'subtask-complete-btn--done': subtask.is_completed }"
                      :disabled="subtask.is_completed || completingSubtaskId === subtask.id"
                      @click="completeSubtask(subtask, task.id)"
                    >
                      <span v-if="completingSubtaskId === subtask.id" class="loading-spinner loading-spinner--sm"></span>
                      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </button>
                    <span class="subtask-title" :class="{ 'subtask-title--done': subtask.is_completed }">
                      {{ subtask.title }}
                    </span>
                    <button
                      class="subtask-delete-btn"
                      :disabled="deletingSubtaskId === subtask.id"
                      @click="deleteSubtask(subtask, task.id)"
                      aria-label="删除子任务"
                    >
                      <span v-if="deletingSubtaskId === subtask.id" class="loading-spinner loading-spinner--sm"></span>
                      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div v-else class="subtask-empty">
                  暂无子任务
                </div>

                <form class="subtask-add-form" @submit.prevent="addSubtask(task.id)">
                  <input
                    v-model="newSubtaskTitle"
                    type="text"
                    class="subtask-input"
                    placeholder="添加子任务..."
                    maxlength="200"
                  />
                  <button
                    type="submit"
                    class="subtask-add-btn"
                    :disabled="!newSubtaskTitle.trim() || creatingSubtask"
                  >
                    <span v-if="creatingSubtask" class="loading-spinner loading-spinner--sm"></span>
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                  </button>
                </form>
              </template>
            </div>
          </div>
          <div class="todo-card-footer">
            <div class="todo-card-stats">
              <span v-if="task.deadline" class="stat-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 8v4l3 3" />
                </svg>
                {{ formatDate(task.deadline) }}
              </span>
              <span class="stat-item stat-item--coins">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v12M6 12h12" />
                </svg>
                +{{ task.coins_reward }}
              </span>
              <span class="stat-item stat-item--exp">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
                +{{ task.exp_reward }} XP
              </span>
            </div>
          </div>
        </div>
      </template>

      <!-- Goals List -->
      <template v-if="activeTab === 'goals'">
        <div
          v-for="goal in goals"
          :key="goal.id"
          class="todo-card"
        >
          <div class="todo-card-header">
            <div class="todo-card-main">
              <button
                class="complete-btn"
                :class="{ 'complete-btn--done': goal.status === 'completed' }"
                :disabled="goal.status === 'completed' || completingId === goal.id"
                @click="completeGoal(goal)"
                :aria-label="'Complete ' + goal.title"
              >
                <span v-if="completingId === goal.id" class="loading-spinner loading-spinner--sm"></span>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </button>
              <div class="todo-card-info">
                <h3 class="todo-card-title" :class="{ 'todo-card-title--done': goal.status === 'completed' }">{{ goal.title }}</h3>
                <p v-if="goal.description" class="todo-card-desc">{{ goal.description }}</p>
              </div>
            </div>
            <div class="todo-card-actions">
              <div class="todo-card-meta">
                <span class="difficulty-badge" :class="'difficulty-badge--' + goal.difficulty">
                  {{ goal.difficulty === 'easy' ? '简单' : goal.difficulty === 'medium' ? '中等' : '困难' }}
                </span>
                <span class="status-badge" :class="'status-badge--' + goal.status">
                  {{ formatStatus(goal.status) }}
                </span>
              </div>
              <div class="action-buttons">
                <button class="action-btn action-btn--edit" @click="openEditDialog(goal, 'goals')" aria-label="编辑">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                </button>
                <button class="action-btn action-btn--delete" @click="openDeleteDialog(goal, 'goals')" aria-label="删除">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          <div class="goal-progress-section">
            <div class="goal-progress-info">
              <span class="goal-progress-label">进度</span>
              <span class="goal-progress-value">{{ Math.round(goal.progress || 0) }}%</span>
            </div>
            <div class="goal-progress-bar">
              <div
                class="goal-progress-fill"
                :style="{ width: Math.round(goal.progress || 0) + '%' }"
              ></div>
            </div>
          </div>

          <div class="todo-card-footer">
            <div class="todo-card-stats">
              <span v-if="goal.deadline" class="stat-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 8v4l3 3" />
                </svg>
                {{ formatDate(goal.deadline) }}
              </span>
              <span class="stat-item stat-item--coins">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v12M6 12h12" />
                </svg>
                +{{ goal.coins_reward }}
              </span>
              <span class="stat-item stat-item--exp">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
                +{{ goal.exp_reward }} XP
              </span>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Reward Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="rewardToast" class="reward-toast">
          <div class="reward-toast-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            <span>+{{ rewardToast.coins }} 金币，+{{ rewardToast.exp }} 经验值！</span>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Error Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="errorToast" class="error-toast">
          <div class="error-toast-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span>{{ errorToast }}</span>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Create Dialog -->
    <Teleport to="body">
      <div v-if="showCreateDialog" class="dialog-overlay" @click.self="cancelDialog">
        <div
          class="dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-dialog-title"
          @keydown="trapFocus"
        >
          <div class="dialog-header">
            <h3 id="create-dialog-title" class="dialog-title">{{ isEditing ? '编辑' : '新建' }}{{ activeTabSingular }}</h3>
            <button class="dialog-close" @click="cancelDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveItem">
            <!-- Common fields -->
            <div class="form-group">
              <label class="form-label" for="item-title">标题</label>
              <input
                id="item-title"
                ref="dialogTitleInput"
                v-model="form.title"
                type="text"
                class="form-input"
                :placeholder="activeTabSingular + '标题'"
                required
                maxlength="200"
              />
            </div>
            <div class="form-group">
              <label class="form-label" for="item-description">描述</label>
              <textarea
                id="item-description"
                v-model="form.description"
                class="form-textarea"
                placeholder="可选描述..."
                rows="2"
              ></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="item-difficulty">难度</label>
                <select id="item-difficulty" v-model="form.difficulty" class="form-select">
                  <option value="easy">简单</option>
                  <option value="medium">中等</option>
                  <option value="hard">困难</option>
                </select>
              </div>
              <!-- Habit-specific: frequency -->
              <div v-if="activeTab === 'habits'" class="form-group">
                <label class="form-label" for="item-frequency">频率</label>
                <select id="item-frequency" v-model="form.frequency" class="form-select">
                  <option value="daily">每日</option>
                  <option value="weekly">每周</option>
                  <option value="monthly">每月</option>
                </select>
              </div>
              <!-- Task/Goal-specific: deadline -->
              <div v-if="activeTab === 'tasks' || activeTab === 'goals'" class="form-group">
                <label class="form-label" for="item-deadline">截止日期</label>
                <input
                  id="item-deadline"
                  v-model="form.deadline"
                  type="datetime-local"
                  class="form-input"
                />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="item-coins">金币奖励</label>
                <input
                  id="item-coins"
                  v-model.number="form.coins_reward"
                  type="number"
                  class="form-input"
                  min="0"
                  max="10000"
                  required
                />
              </div>
              <div class="form-group">
                <label class="form-label" for="item-exp">经验值奖励</label>
                <input
                  id="item-exp"
                  v-model.number="form.exp_reward"
                  type="number"
                  class="form-input"
                  min="0"
                  max="10000"
                  required
                />
              </div>
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="creating || !form.title.trim()">
                <span v-if="creating" class="loading-spinner loading-spinner--sm"></span>
                {{ creating ? (isEditing ? '保存中...' : '创建中...') : (isEditing ? '保存' : '创建') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation Dialog -->
    <Teleport to="body">
      <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="closeDeleteDialog">
        <div
          class="dialog dialog--sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-dialog-title"
          @keydown.escape="closeDeleteDialog"
        >
          <div class="dialog-header">
            <h3 id="delete-dialog-title" class="dialog-title">确认删除</h3>
            <button class="dialog-close" @click="closeDeleteDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="delete-message">
              确定要删除「{{ deletingItem?.title }}」吗？此操作不可撤销。
            </p>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="closeDeleteDialog" :disabled="deleting">取消</button>
              <button type="button" class="btn-danger" @click="confirmDelete" :disabled="deleting">
                <span v-if="deleting" class="loading-spinner loading-spinner--sm"></span>
                {{ deleting ? '删除中...' : '删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { todoService } from '../services/todo'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const activeTab = ref('habits')
const habits = ref([])
const tasks = ref([])
const goals = ref([])
const loading = ref(true)
const error = ref(null)
const completingId = ref(null)
const rewardToast = ref(null)
const rewardToastTimeout = ref(null)
const errorToast = ref(null)
const errorToastTimeout = ref(null)

const showCreateDialog = ref(false)
const creating = ref(false)
const dialogError = ref(null)
const dialogTitleInput = ref(null)

const editingItem = ref(null)
const editingType = ref(null)
const showDeleteDialog = ref(false)
const deletingItem = ref(null)
const deletingType = ref(null)
const deleting = ref(false)

// Subtask state
const expandedTaskId = ref(null)
const taskSubtasks = ref({})
const loadingSubtasks = ref(false)
const newSubtaskTitle = ref('')
const creatingSubtask = ref(false)
const completingSubtaskId = ref(null)
const deletingSubtaskId = ref(null)

const tabs = [
  { id: 'habits', label: '日常习惯' },
  { id: 'tasks', label: '普通待办' },
  { id: 'goals', label: '目标' }
]

const defaultForms = {
  habits: {
    title: '',
    description: '',
    difficulty: 'medium',
    frequency: 'daily',
    coins_reward: 10,
    exp_reward: 5
  },
  tasks: {
    title: '',
    description: '',
    difficulty: 'medium',
    deadline: '',
    coins_reward: 10,
    exp_reward: 5
  },
  goals: {
    title: '',
    description: '',
    difficulty: 'medium',
    deadline: '',
    coins_reward: 50,
    exp_reward: 25
  }
}

const form = ref({ ...defaultForms.habits })

const activeTabSingular = computed(() => {
  if (activeTab.value === 'habits') return '习惯'
  if (activeTab.value === 'tasks') return '任务'
  return '目标'
})

const currentList = computed(() => {
  if (activeTab.value === 'habits') return habits.value
  if (activeTab.value === 'tasks') return tasks.value
  return goals.value
})

function getCount(tab) {
  if (tab === 'habits') return habits.value.length
  if (tab === 'tasks') return tasks.value.length
  return goals.value.length
}

function formatStatus(status) {
  const statusMap = {
    'pending': '待开始',
    'in_progress': '进行中',
    'completed': '已完成',
    'cancelled': '已取消'
  }
  return statusMap[status] || status.replace(/_/g, ' ')
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

// Reset form when tab changes
watch(activeTab, () => {
  form.value = { ...defaultForms[activeTab.value] }
})

// Auto-focus title input when dialog opens
watch(showCreateDialog, (open) => {
  if (open) {
    nextTick(() => {
      dialogTitleInput.value?.focus()
    })
  }
})

const isEditing = computed(() => editingItem.value !== null)

function trapFocus(event) {
  if (event.key !== 'Tab') return
  const dialog = event.currentTarget
  const focusable = dialog.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey) {
    if (document.activeElement === first) {
      event.preventDefault()
      last.focus()
    }
  } else {
    if (document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }
}

function showReward(coins, exp) {
  rewardToast.value = { coins, exp }
  if (rewardToastTimeout.value) clearTimeout(rewardToastTimeout.value)
  rewardToastTimeout.value = setTimeout(() => {
    rewardToast.value = null
    rewardToastTimeout.value = null
  }, 3000)
}

function showError(message) {
  errorToast.value = message
  if (errorToastTimeout.value) clearTimeout(errorToastTimeout.value)
  errorToastTimeout.value = setTimeout(() => {
    errorToast.value = null
    errorToastTimeout.value = null
  }, 4000)
}

onUnmounted(() => {
  if (rewardToastTimeout.value) clearTimeout(rewardToastTimeout.value)
  if (errorToastTimeout.value) clearTimeout(errorToastTimeout.value)
})

async function fetchHabits() {
  habits.value = await todoService.getHabits()
}

async function fetchTasks() {
  tasks.value = await todoService.getTasks()
}

async function fetchGoals() {
  goals.value = await todoService.getGoals()
}

async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    await Promise.all([fetchHabits(), fetchTasks(), fetchGoals()])
  } catch (e) {
    error.value = '加载数据失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function completeHabit(habit) {
  if (!habit.is_active || completingId.value) return
  completingId.value = habit.id
  try {
    const updated = await todoService.completeHabit(habit.id)
    const idx = habits.value.findIndex(h => h.id === habit.id)
    if (idx !== -1) {
      habits.value[idx] = updated
    }
    showReward(updated.coins_reward, updated.exp_reward)
    // Refresh user data to update coins/exp in header
    await authStore.fetchUser()
  } catch (e) {
    console.error('Failed to complete habit:', e)
    showError(e.response?.data?.detail || '完成习惯失败，请重试。')
  } finally {
    completingId.value = null
  }
}

async function completeTask(task) {
  if (task.status === 'completed' || completingId.value) return
  completingId.value = task.id
  try {
    const updated = await todoService.completeTask(task.id)
    const idx = tasks.value.findIndex(t => t.id === task.id)
    if (idx !== -1) {
      tasks.value[idx] = updated
    }
    showReward(updated.coins_reward, updated.exp_reward)
    // Refresh user data to update coins/exp in header
    await authStore.fetchUser()
  } catch (e) {
    console.error('Failed to complete task:', e)
    showError(e.response?.data?.detail || '完成任务失败，请重试。')
  } finally {
    completingId.value = null
  }
}

async function completeGoal(goal) {
  if (goal.status === 'completed' || completingId.value) return
  completingId.value = goal.id
  try {
    const updated = await todoService.completeGoal(goal.id)
    const idx = goals.value.findIndex(g => g.id === goal.id)
    if (idx !== -1) {
      goals.value[idx] = updated
    }
    showReward(updated.coins_reward, updated.exp_reward)
    // Refresh user data to update coins/exp in header
    await authStore.fetchUser()
  } catch (e) {
    console.error('Failed to complete goal:', e)
    showError(e.response?.data?.detail || '完成目标失败，请重试。')
  } finally {
    completingId.value = null
  }
}

function getSubtaskProgress(taskId) {
  const subtasks = taskSubtasks.value[taskId]
  if (!subtasks || subtasks.length === 0) return null
  const completed = subtasks.filter(s => s.is_completed).length
  return Math.round((completed / subtasks.length) * 100)
}

async function toggleTaskExpand(task) {
  if (expandedTaskId.value === task.id) {
    expandedTaskId.value = null
    return
  }
  expandedTaskId.value = task.id
  if (!taskSubtasks.value[task.id]) {
    await fetchSubtasks(task.id)
  }
}

async function fetchSubtasks(taskId) {
  loadingSubtasks.value = true
  try {
    const subtasks = await todoService.getSubtasks(taskId)
    taskSubtasks.value[taskId] = subtasks
  } catch (e) {
    console.error('Failed to fetch subtasks:', e)
    showError('加载子任务失败')
  } finally {
    loadingSubtasks.value = false
  }
}

async function addSubtask(taskId) {
  const title = newSubtaskTitle.value.trim()
  if (!title) return
  creatingSubtask.value = true
  try {
    const subtask = await todoService.createSubtask(taskId, { title })
    if (!taskSubtasks.value[taskId]) {
      taskSubtasks.value[taskId] = []
    }
    taskSubtasks.value[taskId].push(subtask)
    newSubtaskTitle.value = ''
  } catch (e) {
    console.error('Failed to create subtask:', e)
    showError(e.response?.data?.detail || '创建子任务失败')
  } finally {
    creatingSubtask.value = false
  }
}

async function completeSubtask(subtask, taskId) {
  if (subtask.is_completed || completingSubtaskId.value) return
  completingSubtaskId.value = subtask.id
  try {
    const updated = await todoService.completeSubtask(subtask.id)
    const subtasks = taskSubtasks.value[taskId]
    if (subtasks) {
      const idx = subtasks.findIndex(s => s.id === subtask.id)
      if (idx !== -1) {
        subtasks[idx] = updated
      }
    }
  } catch (e) {
    console.error('Failed to complete subtask:', e)
    showError(e.response?.data?.detail || '完成子任务失败')
  } finally {
    completingSubtaskId.value = null
  }
}

async function deleteSubtask(subtask, taskId) {
  deletingSubtaskId.value = subtask.id
  try {
    await todoService.deleteSubtask(subtask.id)
    const subtasks = taskSubtasks.value[taskId]
    if (subtasks) {
      taskSubtasks.value[taskId] = subtasks.filter(s => s.id !== subtask.id)
    }
  } catch (e) {
    console.error('Failed to delete subtask:', e)
    showError(e.response?.data?.detail || '删除子任务失败')
  } finally {
    deletingSubtaskId.value = null
  }
}

function cancelDialog() {
  showCreateDialog.value = false
  editingItem.value = null
  editingType.value = null
  form.value = { ...defaultForms[activeTab.value] }
  dialogError.value = null
}

async function createItem() {
  if (!form.value.title.trim()) return
  creating.value = true
  dialogError.value = null
  try {
    const base = {
      title: form.value.title.trim(),
      description: form.value.description?.trim() || undefined,
      difficulty: form.value.difficulty,
      coins_reward: form.value.coins_reward,
      exp_reward: form.value.exp_reward
    }

    // Add optional deadline for tasks/goals
    if (form.value.deadline) {
      base.deadline = new Date(form.value.deadline).toISOString()
    }

    if (activeTab.value === 'habits') {
      const payload = { ...base, frequency: form.value.frequency }
      const habit = await todoService.createHabit(payload)
      habits.value.push(habit)
    } else if (activeTab.value === 'tasks') {
      const task = await todoService.createTask(base)
      tasks.value.push(task)
    } else {
      const goal = await todoService.createGoal(base)
      goals.value.push(goal)
    }
    cancelDialog()
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '创建失败，请重试。'
  } finally {
    creating.value = false
  }
}

function openEditDialog(item, type) {
  editingItem.value = item
  editingType.value = type
  const deadlineValue = item.deadline
    ? new Date(item.deadline).toISOString().slice(0, 16)
    : ''
  form.value = {
    title: item.title || '',
    description: item.description || '',
    difficulty: item.difficulty || 'medium',
    frequency: item.frequency || 'daily',
    deadline: deadlineValue,
    coins_reward: item.coins_reward ?? 10,
    exp_reward: item.exp_reward ?? 5
  }
  // Switch to the correct tab so the dialog shows the right fields
  if (type !== activeTab.value) {
    activeTab.value = type
  }
  showCreateDialog.value = true
}

async function saveItem() {
  if (!form.value.title.trim()) return
  if (!isEditing.value) {
    return createItem()
  }
  creating.value = true
  dialogError.value = null
  try {
    const base = {
      title: form.value.title.trim(),
      description: form.value.description?.trim() || undefined,
      difficulty: form.value.difficulty,
      coins_reward: form.value.coins_reward,
      exp_reward: form.value.exp_reward
    }

    if (form.value.deadline) {
      base.deadline = new Date(form.value.deadline).toISOString()
    } else if (editingType.value === 'tasks' || editingType.value === 'goals') {
      base.deadline = null
    }

    if (editingType.value === 'habits') {
      base.frequency = form.value.frequency
      const updated = await todoService.updateHabit(editingItem.value.id, base)
      const idx = habits.value.findIndex(h => h.id === editingItem.value.id)
      if (idx !== -1) habits.value[idx] = updated
    } else if (editingType.value === 'tasks') {
      const updated = await todoService.updateTask(editingItem.value.id, base)
      const idx = tasks.value.findIndex(t => t.id === editingItem.value.id)
      if (idx !== -1) tasks.value[idx] = updated
    } else {
      const updated = await todoService.updateGoal(editingItem.value.id, base)
      const idx = goals.value.findIndex(g => g.id === editingItem.value.id)
      if (idx !== -1) goals.value[idx] = updated
    }
    cancelDialog()
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '保存失败，请重试。'
  } finally {
    creating.value = false
  }
}

function openDeleteDialog(item, type) {
  deletingItem.value = item
  deletingType.value = type
  showDeleteDialog.value = true
}

function closeDeleteDialog() {
  showDeleteDialog.value = false
  deletingItem.value = null
  deletingType.value = null
}

async function confirmDelete() {
  if (!deletingItem.value) return
  deleting.value = true
  try {
    if (deletingType.value === 'habits') {
      await todoService.deleteHabit(deletingItem.value.id)
      habits.value = habits.value.filter(h => h.id !== deletingItem.value.id)
    } else if (deletingType.value === 'tasks') {
      await todoService.deleteTask(deletingItem.value.id)
      tasks.value = tasks.value.filter(t => t.id !== deletingItem.value.id)
    } else {
      await todoService.deleteGoal(deletingItem.value.id)
      goals.value = goals.value.filter(g => g.id !== deletingItem.value.id)
    }
    closeDeleteDialog()
  } catch (e) {
    console.error('Failed to delete item:', e)
    showError(e.response?.data?.detail || '删除失败，请重试。')
    closeDeleteDialog()
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  fetchAll()
})
</script>

<style scoped>
.todos-page {
  padding: var(--spacing-xl);
  width: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-md);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.item-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.btn-create {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.btn-create:hover {
  background: var(--color-primary-dark);
}

.btn-create:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-create svg {
  width: 18px;
  height: 18px;
}

/* Tabs */
.tabs {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: var(--font-family);
  transition: color 0.15s ease, border-color 0.15s ease;
  margin-bottom: -1px;
}

.tab-btn:hover {
  color: var(--color-text);
}

.tab-btn--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.tab-icon {
  display: flex;
  align-items: center;
}

.tab-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

.tab-count {
  font-size: var(--font-size-xs);
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
}

.tab-count--habits {
  background: rgba(255, 107, 107, 0.12);
  color: var(--color-error);
}

.tab-count--tasks {
  background: rgba(0, 217, 255, 0.12);
  color: var(--color-secondary);
}

.tab-count--goals {
  background: rgba(108, 99, 255, 0.12);
  color: var(--color-primary);
}

/* Loading State */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-spinner--sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: var(--spacing-md);
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.retry-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.retry-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  text-align: center;
}

.empty-icon {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-xl);
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--spacing-lg);
}

.empty-icon svg {
  width: 36px;
  height: 36px;
  color: var(--color-text-tertiary);
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-sm);
}

.empty-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-xl);
  max-width: 320px;
}

/* Todo List */
.todo-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.todo-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.todo-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.todo-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.todo-card-main {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  flex: 1;
  min-width: 0;
}

.complete-btn {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all 0.15s ease;
}

.complete-btn:hover:not(:disabled) {
  border-color: var(--color-success);
  color: var(--color-success);
  background: rgba(81, 207, 102, 0.1);
}

.complete-btn--done {
  border-color: var(--color-success);
  background: var(--color-success);
  color: #fff;
  cursor: default;
}

.complete-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.complete-btn svg {
  width: 16px;
  height: 16px;
}

.todo-card-info {
  flex: 1;
  min-width: 0;
}

.todo-card-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-xs);
  word-break: break-word;
}

.todo-card-title--done {
  text-decoration: line-through;
  color: var(--color-text-tertiary);
}

.todo-card-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.todo-card-meta {
  display: flex;
  gap: var(--spacing-xs);
  flex-shrink: 0;
}

.difficulty-badge,
.frequency-badge,
.status-badge {
  font-size: var(--font-size-xs);
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-weight: 500;
  text-transform: capitalize;
  white-space: nowrap;
}

.difficulty-badge--easy {
  background: rgba(81, 207, 102, 0.15);
  color: var(--color-success);
}

.difficulty-badge--medium {
  background: rgba(255, 217, 61, 0.15);
  color: var(--color-warning);
}

.difficulty-badge--hard {
  background: rgba(255, 107, 107, 0.15);
  color: var(--color-error);
}

.frequency-badge--daily {
  background: rgba(0, 217, 255, 0.12);
  color: var(--color-secondary);
}

.frequency-badge--weekly {
  background: rgba(108, 99, 255, 0.12);
  color: var(--color-primary);
}

.frequency-badge--monthly {
  background: rgba(255, 107, 107, 0.12);
  color: var(--color-error);
}

.status-badge--pending {
  background: rgba(156, 163, 175, 0.15);
  color: var(--color-text-tertiary);
}

.status-badge--in_progress {
  background: rgba(0, 217, 255, 0.12);
  color: var(--color-secondary);
}

.status-badge--completed {
  background: rgba(81, 207, 102, 0.15);
  color: var(--color-success);
}

.status-badge--cancelled {
  background: rgba(255, 107, 107, 0.12);
  color: var(--color-error);
}

/* Goal Progress */
.goal-progress-section {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border);
}

.goal-progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xs);
}

.goal-progress-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.goal-progress-value {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  font-weight: 700;
}

.goal-progress-bar {
  height: 8px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.goal-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

/* Subtask Section */
.subtask-section {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border);
}

.subtask-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  background: none;
  border: none;
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  font-family: var(--font-family);
  padding: var(--spacing-xs) 0;
  transition: color 0.15s ease;
}

.subtask-toggle-btn:hover {
  color: var(--color-text);
}

.subtask-toggle-icon {
  width: 16px;
  height: 16px;
  transition: transform 0.2s ease;
}

.subtask-toggle-icon--expanded {
  transform: rotate(180deg);
}

.subtask-count-badge {
  font-size: var(--font-size-xs);
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: rgba(108, 99, 255, 0.12);
  color: var(--color-primary);
}

.subtask-content {
  margin-top: var(--spacing-sm);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.subtask-loading {
  display: flex;
  justify-content: center;
  padding: var(--spacing-md) 0;
}

.subtask-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.subtask-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  transition: opacity 0.2s ease;
}

.subtask-item--done {
  opacity: 0.6;
}

.subtask-complete-btn {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all 0.15s ease;
}

.subtask-complete-btn:hover:not(:disabled) {
  border-color: var(--color-success);
  color: var(--color-success);
  background: rgba(81, 207, 102, 0.1);
}

.subtask-complete-btn--done {
  border-color: var(--color-success);
  background: var(--color-success);
  color: #fff;
  cursor: default;
}

.subtask-complete-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.subtask-complete-btn svg {
  width: 12px;
  height: 12px;
}

.subtask-title {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text);
  min-width: 0;
  word-break: break-word;
}

.subtask-title--done {
  text-decoration: line-through;
  color: var(--color-text-tertiary);
}

.subtask-delete-btn {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all 0.15s ease;
  opacity: 0;
}

.subtask-item:hover .subtask-delete-btn {
  opacity: 1;
}

.subtask-delete-btn:hover {
  color: var(--color-error);
  background: rgba(255, 107, 107, 0.08);
}

.subtask-delete-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.subtask-delete-btn svg {
  width: 14px;
  height: 14px;
}

.subtask-empty {
  text-align: center;
  padding: var(--spacing-md) 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.subtask-add-form {
  display: flex;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
}

.subtask-input {
  flex: 1;
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color 0.15s ease;
}

.subtask-input::placeholder {
  color: var(--color-text-tertiary);
}

.subtask-input:focus {
  border-color: var(--color-primary);
}

.subtask-add-btn {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: #fff;
  transition: background 0.15s ease;
}

.subtask-add-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.subtask-add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.subtask-add-btn svg {
  width: 16px;
  height: 16px;
}

/* Footer Stats */
.todo-card-footer {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border);
}

.todo-card-stats {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  flex-wrap: wrap;
}

.stat-item {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.stat-item svg {
  width: 14px;
  height: 14px;
}

.stat-item--coins {
  color: var(--color-warning);
}

.stat-item--exp {
  color: var(--color-primary);
}

/* Reward Toast */
.reward-toast {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: 1100;
}

.reward-toast-content {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-success);
  color: #fff;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  box-shadow: var(--shadow-lg);
}

.reward-toast-content svg {
  width: 18px;
  height: 18px;
}

/* Error Toast */
.error-toast {
  position: fixed;
  top: calc(var(--spacing-lg) + 60px);
  right: var(--spacing-lg);
  z-index: 1100;
}

.error-toast-content {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-error);
  color: #fff;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  box-shadow: var(--shadow-lg);
}

.error-toast-content svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.toast-enter-active {
  transition: all 0.3s ease;
}

.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* Dialog */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.dialog {
  width: 100%;
  max-width: 480px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.dialog-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
}

.dialog-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: background 0.15s ease;
}

.dialog-close:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.dialog-close svg {
  width: 18px;
  height: 18px;
}

.dialog-body {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.form-input,
.form-textarea,
.form-select {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color 0.15s ease;
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  border-color: var(--color-primary);
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: var(--color-text-tertiary);
}

.form-textarea {
  resize: vertical;
  min-height: 60px;
}

.form-select {
  appearance: auto;
  cursor: pointer;
}

.dialog-error {
  font-size: var(--font-size-sm);
  color: var(--color-error);
  padding: var(--spacing-xs) 0;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-sm);
}

.btn-secondary {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.btn-secondary:hover {
  background: var(--color-bg-tertiary);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.btn-primary:hover {
  background: var(--color-primary-dark);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Card Actions */
.todo-card-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}

.action-buttons {
  display: flex;
  gap: var(--spacing-xs);
  opacity: 0;
  transition: opacity 0.15s ease;
}

.todo-card:hover .action-buttons {
  opacity: 1;
}

.action-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all 0.15s ease;
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.action-btn--edit:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(108, 99, 255, 0.08);
}

.action-btn--delete:hover {
  border-color: var(--color-error);
  color: var(--color-error);
  background: rgba(255, 107, 107, 0.08);
}

/* Delete Dialog */
.dialog--sm {
  max-width: 400px;
}

.delete-message {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--spacing-md);
}

.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-error);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.btn-danger:hover {
  background: #e05555;
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 1199px) {
  .todos-page {
    padding: var(--spacing-lg);
  }
}

@media (max-width: 767px) {
  .todos-page {
    padding: var(--spacing-md);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: var(--spacing-xs);
  }

  .tab-btn {
    white-space: nowrap;
    padding: var(--spacing-xs) var(--spacing-md);
    font-size: var(--font-size-xs);
  }

  .todo-card-header {
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .todo-card-meta {
    flex-wrap: wrap;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .dialog {
    max-width: 100%;
    margin: var(--spacing-sm);
  }

  .dialog-body {
    padding: var(--spacing-md);
  }
}
</style>
