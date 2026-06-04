<template>
  <div class="project-detail-page">
    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchData">重试</button>
    </div>

    <template v-else-if="project">
      <!-- Header -->
      <div class="detail-header">
        <div class="detail-header-top">
          <router-link to="/projects" class="back-link">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            返回
          </router-link>
        </div>
        <div class="detail-header-main">
          <div class="detail-header-info">
            <div class="detail-title-row">
              <span class="project-color-dot" :style="{ background: project.color || 'var(--color-primary)' }"></span>
              <h2 class="detail-title">{{ project.name }}</h2>
              <span class="status-badge" :class="'status-badge--' + project.status">
                {{ formatStatus(project.status) }}
              </span>
            </div>
            <p v-if="project.description" class="detail-desc" :class="{ 'detail-desc--collapsed': descCollapsed }">
              {{ project.description }}
            </p>
            <button v-if="project.description && project.description.length > 120" class="desc-toggle" @click="descCollapsed = !descCollapsed">
              {{ descCollapsed ? '展开' : '收起' }}
            </button>
          </div>
          <div class="detail-actions">
            <button class="btn-outline" @click="openEditProject">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
              编辑
            </button>
            <button v-if="project.status !== 'completed'" class="btn-outline btn-outline--success" @click="completeProject">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M20 6L9 17l-5-5" />
              </svg>
              完成项目
            </button>
            <button class="btn-outline btn-outline--danger" @click="showDeleteDialog = true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              删除
            </button>
          </div>
        </div>
        <div class="detail-progress">
          <div class="progress-info">
            <span>{{ project.completed_tasks || 0 }}/{{ project.total_tasks || 0 }} 任务完成 ({{ getProgress(project) }}%)</span>
          </div>
          <div class="progress-bar-lg">
            <div
              class="progress-fill-lg"
              :style="{ width: getProgress(project) + '%', background: project.color || 'var(--color-primary)' }"
            ></div>
          </div>
        </div>
        <div class="detail-dates" v-if="project.start_date || project.end_date">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <span>{{ formatDateFull(project.start_date) || '未设定' }} ~ {{ formatDateFull(project.end_date) || '未设定' }}</span>
        </div>
      </div>

      <!-- View Toggle -->
      <div class="view-toggle">
        <button
          v-for="v in views"
          :key="v.id"
          class="view-btn"
          :class="{ 'view-btn--active': currentView === v.id }"
          @click="currentView = v.id"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path v-if="v.id === 'list'" d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
            <template v-else-if="v.id === 'kanban'">
              <rect x="3" y="3" width="5" height="18" rx="1" />
              <rect x="10" y="3" width="5" height="12" rx="1" />
              <rect x="17" y="3" width="5" height="8" rx="1" />
            </template>
            <template v-else>
              <rect x="3" y="4" width="18" height="4" rx="1" />
              <rect x="3" y="10" width="14" height="4" rx="1" />
              <rect x="3" y="16" width="10" height="4" rx="1" />
            </template>
          </svg>
          {{ v.label }}
        </button>
      </div>

      <!-- List View -->
      <div v-if="currentView === 'list'" class="list-view">
        <!-- Milestone Timeline -->
        <div class="milestone-section">
          <div class="section-header-row">
            <h3 class="section-title">里程碑</h3>
            <button class="btn-sm" @click="openMilestoneDialog()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
              添加
            </button>
          </div>
          <div v-if="milestones.length > 0" class="milestone-timeline">
            <div class="timeline-line"></div>
            <div
              v-for="ms in milestones"
              :key="ms.id"
              class="milestone-node"
              :class="{ 'milestone-node--reached': ms.reached_at }"
              @click="openMilestoneDialog(ms)"
            >
              <div class="milestone-diamond">
                <svg viewBox="0 0 16 16" fill="currentColor"><polygon points="8,1 15,8 8,15 1,8" /></svg>
              </div>
              <span class="milestone-label">{{ ms.title }}</span>
              <span v-if="ms.due_date" class="milestone-date">{{ formatDateShort(ms.due_date) }}</span>
            </div>
          </div>
          <p v-else class="section-empty">暂无里程碑</p>
        </div>

        <!-- Phase Groups -->
        <div v-for="phase in sortedPhases" :key="phase.id" class="phase-group">
          <div class="phase-header" @click="togglePhase(phase.id)">
            <svg class="phase-toggle-icon" :class="{ 'phase-toggle-icon--expanded': expandedPhases.has(phase.id) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
            <span class="phase-name">{{ phase.name }}</span>
            <span class="status-badge status-badge--sm" :class="'status-badge--' + (phase.status || 'active')">{{ formatStatus(phase.status || 'active') }}</span>
            <span class="phase-count">{{ getPhaseTasks(phase.id).length }}</span>
            <div class="phase-actions" @click.stop>
              <button class="btn-icon" @click="openPhaseDialog(phase)" aria-label="编辑">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
              </button>
              <button class="btn-icon btn-icon--danger" @click="deletePhase(phase)" aria-label="删除">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
              </button>
            </div>
          </div>
          <div v-if="expandedPhases.has(phase.id)" class="phase-body">
            <div v-for="task in getPhaseTasks(phase.id)" :key="task.id" class="task-card" :style="{ borderLeftColor: getPriorityColor(task.priority) }">
              <div class="task-card-main">
                <button class="task-complete-btn" :class="{ 'task-complete-btn--done': task.status === 'completed' }" :disabled="task.status === 'completed'" @click="completeTaskCard(task)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12" /></svg>
                </button>
                <div class="task-card-info">
                  <span class="task-card-title" :class="{ 'task-card-title--done': task.status === 'completed' }">{{ task.title }}</span>
                  <span class="task-card-meta">
                    <span class="task-status-badge" :class="'task-status-badge--' + task.status">{{ formatTaskStatus(task.status) }}</span>
                    <span v-if="task.deadline" class="task-deadline">{{ formatDateShort(task.deadline) }}</span>
                  </span>
                </div>
              </div>
            </div>
            <form class="inline-add-form" @submit.prevent="addTaskToPhase(phase.id, $event)">
              <input type="text" class="inline-add-input" placeholder="添加任务..." maxlength="200" />
              <button type="submit" class="btn-sm">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
              </button>
            </form>
          </div>
        </div>

        <!-- Unphased Tasks -->
        <div class="phase-group">
          <div class="phase-header" @click="togglePhase('__unphased')">
            <svg class="phase-toggle-icon" :class="{ 'phase-toggle-icon--expanded': expandedPhases.has('__unphased') }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
            <span class="phase-name">未分类</span>
            <span class="phase-count">{{ unphasedTasks.length }}</span>
          </div>
          <div v-if="expandedPhases.has('__unphased')" class="phase-body">
            <div v-for="task in unphasedTasks" :key="task.id" class="task-card" :style="{ borderLeftColor: getPriorityColor(task.priority) }">
              <div class="task-card-main">
                <button class="task-complete-btn" :class="{ 'task-complete-btn--done': task.status === 'completed' }" :disabled="task.status === 'completed'" @click="completeTaskCard(task)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12" /></svg>
                </button>
                <div class="task-card-info">
                  <span class="task-card-title" :class="{ 'task-card-title--done': task.status === 'completed' }">{{ task.title }}</span>
                  <span class="task-card-meta">
                    <span class="task-status-badge" :class="'task-status-badge--' + task.status">{{ formatTaskStatus(task.status) }}</span>
                    <span v-if="task.deadline" class="task-deadline">{{ formatDateShort(task.deadline) }}</span>
                  </span>
                </div>
              </div>
            </div>
            <form class="inline-add-form" @submit.prevent="addTaskToPhase(null, $event)">
              <input type="text" class="inline-add-input" placeholder="添加任务..." maxlength="200" />
              <button type="submit" class="btn-sm">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
              </button>
            </form>
          </div>
        </div>

        <!-- Add Phase -->
        <button class="btn-add-phase" @click="openPhaseDialog()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
          添加阶段
        </button>
      </div>

      <!-- Kanban View -->
      <div v-if="currentView === 'kanban'" class="kanban-view">
        <div class="kanban-columns">
          <div
            v-for="col in kanbanColumns"
            :key="col.status"
            class="kanban-column"
            @dragover.prevent="onDragOver"
            @drop="onDrop($event, col.status)"
          >
            <div class="kanban-col-header">
              <span class="kanban-col-title">{{ col.label }}</span>
              <span class="kanban-col-count">{{ getKanbanTasks(col.status).length }}</span>
            </div>
            <div class="kanban-col-body">
              <div
                v-for="task in getKanbanTasks(col.status)"
                :key="task.id"
                class="kanban-card"
                :style="{ borderLeftColor: getPriorityColor(task.priority) }"
                draggable="true"
                @dragstart="onDragStart($event, task)"
              >
                <span class="kanban-card-title">{{ task.title }}</span>
                <div class="kanban-card-meta">
                  <span class="priority-dot" :style="{ background: getPriorityColor(task.priority) }"></span>
                  <span v-if="task.deadline" class="task-deadline">{{ formatDateShort(task.deadline) }}</span>
                  <span v-if="task.phase_id" class="phase-label">{{ getPhaseName(task.phase_id) }}</span>
                </div>
              </div>
              <div v-if="col.status === 'pending'" class="kanban-add">
                <form @submit.prevent="addKanbanTask($event)">
                  <input type="text" class="inline-add-input" placeholder="添加任务..." maxlength="200" />
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Gantt View -->
      <div v-if="currentView === 'gantt'" class="gantt-view">
        <div class="gantt-controls">
          <button class="gantt-scale-btn" :class="{ 'gantt-scale-btn--active': ganttScale === 'week' }" @click="ganttScale = 'week'">周</button>
          <button class="gantt-scale-btn" :class="{ 'gantt-scale-btn--active': ganttScale === 'month' }" @click="ganttScale = 'month'">月</button>
        </div>
        <div class="gantt-container">
          <div class="gantt-labels">
            <div v-for="task in ganttTasks" :key="task.id" class="gantt-label" :class="{ 'gantt-label--phase': task._isPhase }">
              {{ task._isPhase ? task.name : task.title }}
            </div>
          </div>
          <div class="gantt-chart-scroll">
            <svg :width="ganttWidth" :height="ganttHeight" class="gantt-svg">
              <!-- Grid lines -->
              <line
                v-for="(line, i) in ganttGridLines"
                :key="'g' + i"
                :x1="line.x"
                :y1="0"
                :x2="line.x"
                :y2="ganttHeight"
                stroke="var(--color-border)"
                stroke-width="1"
                stroke-dasharray="4,4"
              />
              <!-- Time labels -->
              <text
                v-for="(label, i) in ganttTimeLabels"
                :key="'t' + i"
                :x="label.x"
                :y="16"
                fill="var(--color-text-tertiary)"
                font-size="12"
                text-anchor="middle"
              >{{ label.text }}</text>
              <!-- Task bars -->
              <template v-for="(task, i) in ganttTasks" :key="'b' + task.id">
                <rect
                  v-if="!task._isPhase && getGanttBar(task)"
                  :x="getGanttBar(task).x"
                  :y="getGanttBar(task).y"
                  :width="getGanttBar(task).w"
                  :height="30"
                  :rx="4"
                  :fill="project.color || 'var(--color-primary)'"
                  :opacity="task.status === 'completed' ? 0.4 : 0.8"
                />
                <!-- Dot for tasks without start_date -->
                <circle
                  v-if="!task._isPhase && !task.start_date && task.deadline"
                  :cx="getGanttBar(task)?.x || ganttDateToX(task.deadline)"
                  :cy="(ganttTasks.indexOf(task)) * 40 + 25 + 20"
                  r="4"
                  :fill="project.color || 'var(--color-primary)'"
                />
              </template>
              <!-- Milestone diamonds -->
              <polygon
                v-for="ms in ganttMilestones"
                :key="'ms' + ms.id"
                :points="getMilestoneDiamond(ms)"
                :fill="ms.reached_at ? 'var(--color-success)' : 'var(--color-text-tertiary)'"
              />
              <!-- Today line -->
              <line
                :x1="ganttTodayX"
                :y1="0"
                :x2="ganttTodayX"
                :y2="ganttHeight"
                stroke="var(--color-error)"
                stroke-width="2"
                stroke-dasharray="6,3"
              />
            </svg>
          </div>
        </div>
      </div>
    </template>

    <!-- Task Create/Edit Dialog -->
    <Teleport to="body">
      <div v-if="showTaskDialog" class="dialog-overlay" @click.self="cancelTaskDialog">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">编辑任务</h3>
            <button class="dialog-close" @click="cancelTaskDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveTask">
            <div class="form-group">
              <label class="form-label" for="task-title">标题</label>
              <input id="task-title" v-model="taskForm.title" type="text" class="form-input" placeholder="任务标题" required maxlength="200" />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="task-priority">优先级</label>
                <select id="task-priority" v-model="taskForm.priority" class="form-input">
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                  <option value="urgent">紧急</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label" for="task-phase">阶段</label>
                <select id="task-phase" v-model="taskForm.phase_id" class="form-input">
                  <option :value="null">未分类</option>
                  <option v-for="ph in phases" :key="ph.id" :value="ph.id">{{ ph.name }}</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="task-start">开始日期</label>
                <input id="task-start" v-model="taskForm.start_date" type="date" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label" for="task-deadline">截止日期</label>
                <input id="task-deadline" v-model="taskForm.deadline" type="date" class="form-input" />
              </div>
            </div>
            <div v-if="taskDialogError" class="dialog-error">{{ taskDialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelTaskDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="!taskForm.title.trim()">保存</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Phase Create/Edit Dialog -->
    <Teleport to="body">
      <div v-if="showPhaseDialog" class="dialog-overlay" @click.self="cancelPhaseDialog">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">{{ editingPhase ? '编辑阶段' : '新建阶段' }}</h3>
            <button class="dialog-close" @click="cancelPhaseDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="savePhase">
            <div class="form-group">
              <label class="form-label" for="phase-name">名称</label>
              <input id="phase-name" v-model="phaseForm.name" type="text" class="form-input" placeholder="阶段名称" required maxlength="200" />
            </div>
            <div v-if="phaseDialogError" class="dialog-error">{{ phaseDialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelPhaseDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="!phaseForm.name.trim()">保存</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Milestone Create/Edit Dialog -->
    <Teleport to="body">
      <div v-if="showMilestoneDialog" class="dialog-overlay" @click.self="cancelMilestoneDialog">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">{{ editingMilestone ? '编辑里程碑' : '新建里程碑' }}</h3>
            <button class="dialog-close" @click="cancelMilestoneDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveMilestone">
            <div class="form-group">
              <label class="form-label" for="ms-title">标题</label>
              <input id="ms-title" v-model="msForm.title" type="text" class="form-input" placeholder="里程碑标题" required maxlength="200" />
            </div>
            <div class="form-group">
              <label class="form-label" for="ms-date">截止日期</label>
              <input id="ms-date" v-model="msForm.due_date" type="date" class="form-input" />
            </div>
            <div v-if="msDialogError" class="dialog-error">{{ msDialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelMilestoneDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="!msForm.title.trim()">保存</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Edit Project Dialog -->
    <Teleport to="body">
      <div v-if="showEditProjectDialog" class="dialog-overlay" @click.self="cancelEditProjectDialog">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">编辑项目</h3>
            <button class="dialog-close" @click="cancelEditProjectDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveEditProject">
            <div class="form-group">
              <label class="form-label" for="edit-name">名称</label>
              <input id="edit-name" v-model="editForm.name" type="text" class="form-input" required maxlength="200" />
            </div>
            <div class="form-group">
              <label class="form-label" for="edit-desc">描述</label>
              <textarea id="edit-desc" v-model="editForm.description" class="form-textarea" rows="2"></textarea>
            </div>
            <div class="form-group">
              <label class="form-label">颜色</label>
              <div class="color-picker">
                <button v-for="c in presetColors" :key="c" type="button" class="color-dot" :class="{ 'color-dot--active': editForm.color === c }" :style="{ background: c }" @click="editForm.color = c"></button>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="edit-start">开始日期</label>
                <input id="edit-start" v-model="editForm.start_date" type="date" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label" for="edit-end">结束日期</label>
                <input id="edit-end" v-model="editForm.end_date" type="date" class="form-input" />
              </div>
            </div>
            <div v-if="editDialogError" class="dialog-error">{{ editDialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelEditProjectDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="!editForm.name.trim()">保存</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation Dialog -->
    <Teleport to="body">
      <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="showDeleteDialog = false">
        <div class="dialog dialog--sm" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">确认删除</h3>
            <button class="dialog-close" @click="showDeleteDialog = false" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="delete-message">确定要删除项目「{{ project?.name }}」吗？此操作不可撤销。</p>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="showDeleteDialog = false" :disabled="deleting">取消</button>
              <button type="button" class="btn-danger" @click="confirmDeleteProject" :disabled="deleting">
                <span v-if="deleting" class="loading-spinner loading-spinner--sm"></span>
                {{ deleting ? '删除中...' : '删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="errorToast" class="error-toast" role="status" aria-live="polite">
          <div class="error-toast-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
            <span>{{ errorToast }}</span>
          </div>
        </div>
      </Transition>
      <Transition name="toast">
        <div v-if="successToast" class="success-toast" role="status" aria-live="polite">
          <div class="success-toast-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12" /></svg>
            <span>{{ successToast }}</span>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { projectService } from '../services/project'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const { successToast, errorToast, showSuccess, showError } = useToast()

const projectId = route.params.id

// Core data
const project = ref(null)
const phases = ref([])
const milestones = ref([])
const tasks = ref([])
const loading = ref(true)
const error = ref(null)
const deleting = ref(false)
const descCollapsed = ref(true)

// View state
const currentView = ref('list')
const views = [
  { id: 'list', label: '列表' },
  { id: 'kanban', label: '看板' },
  { id: 'gantt', label: '甘特图' }
]

// Phase expand state
const expandedPhases = reactive(new Set())

// Kanban columns
const kanbanColumns = [
  { status: 'pending', label: '待办' },
  { status: 'in_progress', label: '进行中' },
  { status: 'completed', label: '已完成' },
  { status: 'cancelled', label: '已取消' }
]

// Gantt
const ganttScale = ref('week')

// Preset colors
const presetColors = ['#6c63ff', '#00d9ff', '#51cf66', '#ff6b6b', '#ffd93d', '#ff922b', '#845ef7', '#20c997']

// Dialogs
const showTaskDialog = ref(false)
const editingTask = ref(null)
const taskForm = ref({ title: '', priority: 'medium', phase_id: null, start_date: '', deadline: '' })
const taskDialogError = ref(null)

const showPhaseDialog = ref(false)
const editingPhase = ref(null)
const phaseForm = ref({ name: '' })
const phaseDialogError = ref(null)

const showMilestoneDialog = ref(false)
const editingMilestone = ref(null)
const msForm = ref({ title: '', due_date: '' })
const msDialogError = ref(null)

const showEditProjectDialog = ref(false)
const editForm = ref({ name: '', description: '', color: '', start_date: '', end_date: '' })
const editDialogError = ref(null)

const showDeleteDialog = ref(false)

// Drag state
let draggedTask = null

// Computed
const sortedPhases = computed(() => {
  return [...phases.value].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
})

const unphasedTasks = computed(() => {
  return tasks.value.filter(t => !t.phase_id)
})

function getPhaseTasks(phaseId) {
  return tasks.value.filter(t => t.phase_id === phaseId)
}

function getProgress(p) {
  if (!p || !p.total_tasks || p.total_tasks === 0) return 0
  return Math.round(((p.completed_tasks || 0) / p.total_tasks) * 100)
}

function formatStatus(status) {
  const map = { planning: '规划中', active: '进行中', completed: '已完成', archived: '已归档' }
  return map[status] || status
}

function formatTaskStatus(status) {
  const map = { pending: '待办', in_progress: '进行中', completed: '已完成', cancelled: '已取消' }
  return map[status] || status
}

function formatDateFull(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatDateShort(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function getPriorityColor(priority) {
  const map = { urgent: '#ff6b6b', high: '#ff922b', medium: '#00d9ff', low: '#9ca3af' }
  return map[priority] || map.medium
}

function getPhaseName(phaseId) {
  const ph = phases.value.find(p => p.id === phaseId)
  return ph?.name || ''
}

function togglePhase(id) {
  if (expandedPhases.has(id)) expandedPhases.delete(id)
  else expandedPhases.add(id)
}

function getKanbanTasks(status) {
  return tasks.value.filter(t => t.status === status)
}

// --- Data Fetching ---
async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const [proj, taskList] = await Promise.all([
      projectService.getProject(projectId),
      projectService.getProjectTasks(projectId)
    ])
    project.value = proj
    phases.value = proj.phases || []
    milestones.value = proj.milestones || []
    tasks.value = taskList || []
    // Expand first phase by default
    if (phases.value.length > 0) expandedPhases.add(phases.value[0].id)
    expandedPhases.add('__unphased')
  } catch (e) {
    error.value = '加载项目失败，请重试。'
  } finally {
    loading.value = false
  }
}

// --- Task operations ---
function addTaskToPhase(phaseId, event) {
  const input = event.target.querySelector('input')
  const title = input?.value?.trim()
  if (!title) return
  projectService.createTask(projectId, { title, phase_id: phaseId }).then(task => {
    tasks.value.push(task)
    input.value = ''
    if (project.value) {
      project.value.total_tasks = (project.value.total_tasks || 0) + 1
    }
  }).catch(e => {
    showError(e.response?.data?.detail || '创建任务失败')
  })
}

function addKanbanTask(event) {
  const input = event.target.querySelector('input')
  const title = input?.value?.trim()
  if (!title) return
  projectService.createTask(projectId, { title, status: 'pending' }).then(task => {
    tasks.value.push(task)
    input.value = ''
    if (project.value) {
      project.value.total_tasks = (project.value.total_tasks || 0) + 1
    }
  }).catch(e => {
    showError(e.response?.data?.detail || '创建任务失败')
  })
}

async function completeTaskCard(task) {
  try {
    const updated = await projectService.moveTask(task.id, { status: 'completed' })
    const idx = tasks.value.findIndex(t => t.id === task.id)
    if (idx !== -1) tasks.value[idx] = { ...tasks.value[idx], ...updated }
    if (project.value) {
      project.value.completed_tasks = (project.value.completed_tasks || 0) + 1
    }
  } catch (e) {
    showError(e.response?.data?.detail || '操作失败')
  }
}

// --- Drag and Drop ---
function onDragStart(event, task) {
  draggedTask = task
  event.dataTransfer.effectAllowed = 'move'
}

function onDragOver(event) {
  event.dataTransfer.dropEffect = 'move'
}

async function onDrop(event, newStatus) {
  event.preventDefault()
  if (!draggedTask || draggedTask.status === newStatus) return
  const oldStatus = draggedTask.status
  const task = draggedTask
  draggedTask = null
  // Optimistic update
  task.status = newStatus
  try {
    await projectService.moveTask(task.id, { status: newStatus })
    // Update completed_tasks count
    if (project.value) {
      if (newStatus === 'completed') project.value.completed_tasks = (project.value.completed_tasks || 0) + 1
      else if (oldStatus === 'completed') project.value.completed_tasks = Math.max(0, (project.value.completed_tasks || 0) - 1)
    }
  } catch (e) {
    task.status = oldStatus
    showError(e.response?.data?.detail || '移动任务失败')
  }
}

// --- Phase operations ---
function openPhaseDialog(phase) {
  editingPhase.value = phase || null
  phaseForm.value = { name: phase?.name || '' }
  phaseDialogError.value = null
  showPhaseDialog.value = true
}

function cancelPhaseDialog() {
  showPhaseDialog.value = false
  editingPhase.value = null
  phaseForm.value = { name: '' }
}

async function savePhase() {
  if (!phaseForm.value.name.trim()) return
  try {
    if (editingPhase.value) {
      const updated = await projectService.updatePhase(editingPhase.value.id, { name: phaseForm.value.name.trim() })
      const idx = phases.value.findIndex(p => p.id === editingPhase.value.id)
      if (idx !== -1) phases.value[idx] = updated
    } else {
      const created = await projectService.createPhase(projectId, { name: phaseForm.value.name.trim() })
      phases.value.push(created)
    }
    cancelPhaseDialog()
  } catch (e) {
    phaseDialogError.value = e.response?.data?.detail || '操作失败'
  }
}

async function deletePhase(phase) {
  try {
    await projectService.deletePhase(phase.id)
    phases.value = phases.value.filter(p => p.id !== phase.id)
    // Move tasks to unphased
    tasks.value.forEach(t => { if (t.phase_id === phase.id) t.phase_id = null })
  } catch (e) {
    showError(e.response?.data?.detail || '删除阶段失败')
  }
}

// --- Milestone operations ---
function openMilestoneDialog(ms) {
  editingMilestone.value = ms || null
  msForm.value = {
    title: ms?.title || '',
    due_date: ms?.due_date ? new Date(ms.due_date).toISOString().slice(0, 10) : ''
  }
  msDialogError.value = null
  showMilestoneDialog.value = true
}

function cancelMilestoneDialog() {
  showMilestoneDialog.value = false
  editingMilestone.value = null
  msForm.value = { title: '', due_date: '' }
}

async function saveMilestone() {
  if (!msForm.value.title.trim()) return
  try {
    const data = { title: msForm.value.title.trim() }
    if (msForm.value.due_date) data.due_date = msForm.value.due_date
    if (editingMilestone.value) {
      const updated = await projectService.updateMilestone(editingMilestone.value.id, data)
      const idx = milestones.value.findIndex(m => m.id === editingMilestone.value.id)
      if (idx !== -1) milestones.value[idx] = updated
    } else {
      const created = await projectService.createMilestone(projectId, data)
      milestones.value.push(created)
    }
    cancelMilestoneDialog()
  } catch (e) {
    msDialogError.value = e.response?.data?.detail || '操作失败'
  }
}

// --- Project edit/complete/delete ---
function openEditProject() {
  editForm.value = {
    name: project.value.name || '',
    description: project.value.description || '',
    color: project.value.color || '#6c63ff',
    start_date: project.value.start_date ? new Date(project.value.start_date).toISOString().slice(0, 10) : '',
    end_date: project.value.end_date ? new Date(project.value.end_date).toISOString().slice(0, 10) : ''
  }
  editDialogError.value = null
  showEditProjectDialog.value = true
}

function cancelEditProjectDialog() {
  showEditProjectDialog.value = false
}

async function saveEditProject() {
  if (!editForm.value.name.trim()) return
  try {
    const data = { name: editForm.value.name.trim(), color: editForm.value.color }
    if (editForm.value.description) data.description = editForm.value.description.trim()
    else data.description = ''
    data.start_date = editForm.value.start_date || null
    data.end_date = editForm.value.end_date || null
    const updated = await projectService.updateProject(projectId, data)
    project.value = updated
    cancelEditProjectDialog()
    showSuccess('项目已更新')
  } catch (e) {
    editDialogError.value = e.response?.data?.detail || '保存失败'
  }
}

async function completeProject() {
  try {
    const updated = await projectService.completeProject(projectId)
    project.value = updated
    showSuccess('项目已完成')
  } catch (e) {
    showError(e.response?.data?.detail || '操作失败')
  }
}

async function confirmDeleteProject() {
  deleting.value = true
  try {
    await projectService.deleteProject(projectId)
    router.push('/projects')
  } catch (e) {
    showError(e.response?.data?.detail || '删除失败')
    showDeleteDialog.value = false
  } finally {
    deleting.value = false
  }
}

// --- Gantt Chart ---
const DAY_MS = 86400000
const ganttRowHeight = 40
const ganttDayWidth = computed(() => ganttScale.value === 'week' ? 40 : 10)
const ganttHeaderHeight = 30

const ganttTasks = computed(() => {
  const result = []
  for (const phase of sortedPhases.value) {
    result.push({ id: 'phase-' + phase.id, name: phase.name, _isPhase: true })
    for (const t of getPhaseTasks(phase.id)) result.push(t)
  }
  if (unphasedTasks.value.length > 0) {
    result.push({ id: 'phase-unphased', name: '未分类', _isPhase: true })
    for (const t of unphasedTasks.value) result.push(t)
  }
  return result
})

const ganttRange = computed(() => {
  let min = Date.now() - 7 * DAY_MS
  let max = Date.now() + 30 * DAY_MS
  for (const t of tasks.value) {
    if (t.start_date) min = Math.min(min, new Date(t.start_date).getTime())
    if (t.deadline) max = Math.max(max, new Date(t.deadline).getTime())
    if (t.created_at) min = Math.min(min, new Date(t.created_at).getTime())
  }
  for (const ms of milestones.value) {
    if (ms.due_date) max = Math.max(max, new Date(ms.due_date).getTime())
  }
  if (project.value?.start_date) min = Math.min(min, new Date(project.value.start_date).getTime())
  if (project.value?.end_date) max = Math.max(max, new Date(project.value.end_date).getTime())
  min = Math.floor(min / DAY_MS) * DAY_MS
  max = Math.ceil(max / DAY_MS) * DAY_MS + DAY_MS
  return { min, max }
})

const ganttWidth = computed(() => {
  const days = Math.ceil((ganttRange.value.max - ganttRange.value.min) / DAY_MS)
  return Math.max(days * ganttDayWidth.value, 800)
})

const ganttHeight = computed(() => ganttTasks.value.length * ganttRowHeight + ganttHeaderHeight + 20)

const ganttTodayX = computed(() => {
  return ((Date.now() - ganttRange.value.min) / DAY_MS) * ganttDayWidth.value
})

const ganttGridLines = computed(() => {
  const lines = []
  const days = Math.ceil((ganttRange.value.max - ganttRange.value.min) / DAY_MS)
  const step = ganttScale.value === 'week' ? 7 : 1
  for (let i = 0; i <= days; i += step) {
    lines.push({ x: i * ganttDayWidth.value })
  }
  return lines
})

const ganttTimeLabels = computed(() => {
  const labels = []
  const days = Math.ceil((ganttRange.value.max - ganttRange.value.min) / DAY_MS)
  const step = ganttScale.value === 'week' ? 7 : 30
  for (let i = 0; i <= days; i += step) {
    const d = new Date(ganttRange.value.min + i * DAY_MS)
    const text = ganttScale.value === 'week'
      ? `${d.getMonth() + 1}/${d.getDate()}`
      : `${d.getFullYear()}/${d.getMonth() + 1}`
    labels.push({ x: i * ganttDayWidth.value + ganttDayWidth.value * step / 2, text })
  }
  return labels
})

const ganttMilestones = computed(() => {
  return milestones.value.filter(ms => ms.due_date)
})

function ganttDateToX(dateStr) {
  return ((new Date(dateStr).getTime() - ganttRange.value.min) / DAY_MS) * ganttDayWidth.value
}

function getGanttBar(task) {
  const idx = ganttTasks.value.indexOf(task)
  if (idx < 0) return null
  const y = idx * ganttRowHeight + ganttHeaderHeight + 5
  const startDate = task.start_date || task.created_at
  if (!startDate && !task.deadline) return null
  const x = startDate ? ganttDateToX(startDate) : ganttDateToX(task.deadline)
  const endX = task.deadline ? ganttDateToX(task.deadline) : x + ganttDayWidth.value * 3
  const w = Math.max(endX - x, ganttDayWidth.value)
  return { x, y, w }
}

function getMilestoneDiamond(ms) {
  const x = ganttDateToX(ms.due_date)
  const y = ganttHeaderHeight
  const s = 6
  return `${x},${y - s} ${x + s},${y} ${x},${y + s} ${x - s},${y}`
}

// --- Init ---
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.project-detail-page {
  padding: var(--spacing-xl);
  width: 100%;
}

/* Header */
.detail-header {
  margin-bottom: var(--spacing-xl);
}

.detail-header-top {
  margin-bottom: var(--spacing-md);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color 0.15s ease;
}

.back-link:hover {
  color: var(--color-primary);
}

.back-link svg {
  width: 16px;
  height: 16px;
}

.detail-header-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.detail-header-info {
  flex: 1;
  min-width: 0;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.project-color-dot {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.detail-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.detail-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.detail-desc--collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.desc-toggle {
  background: none;
  border: none;
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  cursor: pointer;
  padding: 0;
  margin-top: var(--spacing-xs);
  font-family: var(--font-family);
}

.detail-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.btn-outline svg {
  width: 14px;
  height: 14px;
}

.btn-outline:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-outline--success:hover {
  border-color: var(--color-success);
  color: var(--color-success);
}

.btn-outline--danger:hover {
  border-color: var(--color-error);
  color: var(--color-error);
}

/* Progress */
.detail-progress {
  margin-bottom: var(--spacing-md);
}

.progress-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xs);
}

.progress-bar-lg {
  height: 8px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill-lg {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.detail-dates {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.detail-dates svg {
  width: 16px;
  height: 16px;
}

/* View Toggle */
.view-toggle {
  display: flex;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-xl);
}

.view-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.view-btn svg {
  width: 16px;
  height: 16px;
}

.view-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.view-btn--active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.view-btn--active:hover {
  background: var(--color-primary-dark);
  color: #fff;
}

/* Status Badge */
.status-badge {
  font-size: var(--font-size-xs);
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.status-badge--sm {
  padding: 1px 8px;
}

.status-badge--planning { background: rgba(156, 163, 175, 0.15); color: var(--color-text-tertiary); }
.status-badge--active { background: rgba(0, 217, 255, 0.12); color: var(--color-secondary); }
.status-badge--completed { background: rgba(81, 207, 102, 0.15); color: var(--color-success); }
.status-badge--archived { background: rgba(156, 163, 175, 0.15); color: var(--color-text-tertiary); }

/* === LIST VIEW === */
.milestone-section {
  margin-bottom: var(--spacing-xl);
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.section-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.section-empty {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  padding: var(--spacing-md) 0;
}

.milestone-timeline {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  position: relative;
  padding: var(--spacing-md) 0;
  overflow-x: auto;
}

.timeline-line {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--color-border);
  z-index: 0;
}

.milestone-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  position: relative;
  z-index: 1;
  cursor: pointer;
  min-width: 80px;
}

.milestone-diamond {
  width: 20px;
  height: 20px;
  color: var(--color-text-tertiary);
  transition: color 0.15s ease;
}

.milestone-node--reached .milestone-diamond {
  color: var(--color-success);
}

.milestone-label {
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-text);
  text-align: center;
}

.milestone-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* Phase Groups */
.phase-group {
  margin-bottom: var(--spacing-md);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.phase-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer;
  transition: background 0.15s ease;
}

.phase-header:hover {
  background: var(--color-bg-tertiary);
}

.phase-toggle-icon {
  width: 16px;
  height: 16px;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.phase-toggle-icon--expanded {
  transform: rotate(180deg);
}

.phase-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
  flex: 1;
}

.phase-count {
  font-size: var(--font-size-xs);
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
}

.phase-actions {
  display: flex;
  gap: var(--spacing-xs);
  opacity: 0;
  transition: opacity 0.15s ease;
}

.phase-header:hover .phase-actions {
  opacity: 1;
}

.phase-body {
  padding: 0 var(--spacing-lg) var(--spacing-lg);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Task Cards (List View) */
.task-card {
  display: flex;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  margin-bottom: var(--spacing-xs);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-border);
  transition: opacity 0.2s ease;
}

.task-card-main {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex: 1;
  min-width: 0;
}

.task-complete-btn {
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

.task-complete-btn:hover:not(:disabled) {
  border-color: var(--color-success);
  color: var(--color-success);
}

.task-complete-btn--done {
  border-color: var(--color-success);
  background: var(--color-success);
  color: #fff;
  cursor: default;
}

.task-complete-btn:disabled { cursor: not-allowed; opacity: 0.7; }
.task-complete-btn svg { width: 12px; height: 12px; }

.task-card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.task-card-title {
  font-size: var(--font-size-sm);
  color: var(--color-text);
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-card-title--done {
  text-decoration: line-through;
  color: var(--color-text-tertiary);
}

.task-card-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  flex-shrink: 0;
}

.task-status-badge {
  font-size: var(--font-size-xs);
  padding: 1px 8px;
  border-radius: var(--radius-full);
  font-weight: 500;
}

.task-status-badge--pending { background: rgba(156, 163, 175, 0.15); color: var(--color-text-tertiary); }
.task-status-badge--in_progress { background: rgba(0, 217, 255, 0.12); color: var(--color-secondary); }
.task-status-badge--completed { background: rgba(81, 207, 102, 0.15); color: var(--color-success); }
.task-status-badge--cancelled { background: rgba(255, 107, 107, 0.12); color: var(--color-error); }

.task-deadline {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.inline-add-form {
  display: flex;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
}

.inline-add-input {
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

.inline-add-input::placeholder { color: var(--color-text-tertiary); }
.inline-add-input:focus { border-color: var(--color-primary); }

.btn-sm {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.btn-sm svg { width: 14px; height: 14px; }
.btn-sm:hover { background: var(--color-primary); color: #fff; }

.btn-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all 0.15s ease;
}

.btn-icon svg { width: 14px; height: 14px; }
.btn-icon:hover { color: var(--color-primary); background: rgba(108, 99, 255, 0.08); }
.btn-icon--danger:hover { color: var(--color-error); background: rgba(255, 107, 107, 0.08); }

.btn-add-phase {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  width: 100%;
  padding: var(--spacing-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-tertiary);
  background: transparent;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
  margin-top: var(--spacing-md);
}

.btn-add-phase svg { width: 16px; height: 16px; }
.btn-add-phase:hover { border-color: var(--color-primary); color: var(--color-primary); }

/* === KANBAN VIEW === */
.kanban-columns {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  align-items: start;
}

.kanban-column {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  min-height: 200px;
}

.kanban-col-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.kanban-col-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.kanban-col-count {
  font-size: var(--font-size-xs);
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
}

.kanban-col-body {
  padding: var(--spacing-sm);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.kanban-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  cursor: grab;
  transition: box-shadow 0.15s ease, opacity 0.15s ease;
}

.kanban-card:hover {
  box-shadow: var(--shadow-md);
}

.kanban-card:active {
  cursor: grabbing;
  opacity: 0.7;
}

.kanban-card-title {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
  display: block;
  margin-bottom: var(--spacing-xs);
}

.kanban-card-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  flex-wrap: wrap;
}

.priority-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.phase-label {
  font-size: var(--font-size-xs);
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background: rgba(108, 99, 255, 0.12);
  color: var(--color-primary);
}

.kanban-add {
  padding-top: var(--spacing-xs);
}

/* === GANTT VIEW === */
.gantt-controls {
  display: flex;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-md);
}

.gantt-scale-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.gantt-scale-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.gantt-scale-btn--active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.gantt-container {
  display: flex;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.gantt-labels {
  flex-shrink: 0;
  width: 180px;
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.gantt-label {
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.gantt-label--phase {
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-bg-tertiary);
  font-size: var(--font-size-xs);
}

.gantt-chart-scroll {
  overflow-x: auto;
  flex: 1;
}

.gantt-svg {
  display: block;
}

/* === SHARED DIALOG STYLES === */
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

.dialog--sm { max-width: 400px; }

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

.dialog-close:hover { background: var(--color-bg-tertiary); color: var(--color-text); }
.dialog-close svg { width: 18px; height: 18px; }

.dialog-body {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.form-group { display: flex; flex-direction: column; gap: var(--spacing-xs); }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md); }
.form-label { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text); }

.form-input,
.form-textarea {
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
.form-textarea:focus { border-color: var(--color-primary); }
.form-textarea { resize: vertical; min-height: 60px; }

.color-picker {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.color-dot {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  border: 3px solid transparent;
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease;
  padding: 0;
}

.color-dot:hover { transform: scale(1.1); }
.color-dot--active { border-color: var(--color-text); transform: scale(1.15); }

.dialog-error { font-size: var(--font-size-sm); color: var(--color-error); }

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

.btn-secondary:hover { background: var(--color-bg-tertiary); }

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

.btn-primary:hover { background: var(--color-primary-dark); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

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

.btn-danger:hover { background: #e05555; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

.delete-message {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* Toasts */
.error-toast, .success-toast {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: 1100;
}

.error-toast-content, .success-toast-content {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  box-shadow: var(--shadow-lg);
}

.error-toast-content { background: var(--color-error); color: #fff; }
.success-toast-content { background: var(--color-success); color: #fff; }
.error-toast-content svg, .success-toast-content svg { width: 18px; height: 18px; flex-shrink: 0; }

.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(-20px); }

/* Loading / Error */
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

.loading-spinner--sm { width: 16px; height: 16px; border-width: 2px; }

@keyframes spin {
  to { transform: rotate(360deg); }
}

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

.retry-btn:hover { background: var(--color-primary); color: #fff; }

/* Responsive */
@media (max-width: 1199px) {
  .project-detail-page { padding: var(--spacing-lg); }
}

@media (max-width: 767px) {
  .project-detail-page { padding: var(--spacing-md); }

  .detail-header-main {
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .detail-actions {
    flex-wrap: wrap;
  }

  .kanban-columns {
    grid-template-columns: 1fr;
  }

  .kanban-column {
    min-height: auto;
  }

  .gantt-labels {
    width: 120px;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .dialog {
    max-width: 100%;
    margin: var(--spacing-sm);
  }
}
</style>
