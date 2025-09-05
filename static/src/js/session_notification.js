odoo.define('volan_yasamal.session_notification', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var session = require('web.session');
    var _t = core._t;

    var SessionNotification = AbstractAction.extend({
        template: 'SessionNotificationTemplate',
        
        events: {
            'click .set_max_checks': '_onSetMaxChecks',
            'click .reset_checks': '_onResetChecks',
            'click .stop_checks': '_onStopChecks'
        },
        
        init: function(parent, action) {
            this._super.apply(this, arguments);
            this.action = action;
            this.notification_check_interval = 60000; // Check every minute
            this.notification_timeouts = {};
            
            // Counter-based control system
            this.checkCounter = 0;
            this.maxChecks = 0; // 0 means unlimited checks
            this.lastSessionCheck = new Date();
            this.sessionCheckEnabled = true;
            
            // Active sessions tracking
            this.activeSessions = [];
            this.countdownInterval = null;
        },
        
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            
            // Start checking for sessions ending soon
            this._startSessionCheck();
            
            // Setup audio element
            this.audioElement = new Audio('/volan_yasamal/static/src/audio/notification.mp3');
            
            // Initialize counter display
            this._updateCounterDisplay();
            
            // Start countdown timer for active sessions
            this._startCountdownTimer();
            
            return this._super();
        },
        
        _startCountdownTimer: function() {
            var self = this;
            
            // Clear any existing interval
            if (this.countdownInterval) {
                clearInterval(this.countdownInterval);
            }
            
            // Start a new countdown interval that updates every second
            this.countdownInterval = setInterval(function() {
                self._updateCountdowns();
            }, 1000);
            
            // Initial load of active sessions
            this._fetchActiveSessions();
        },
        
        _fetchActiveSessions: function() {
            var self = this;
            
            this._rpc({
                model: 'badminton.session',
                method: 'get_active_sessions',
                args: [],
            }).then(function(result) {
                if (result && result.sessions) {
                    self.activeSessions = result.sessions;
                    self._renderActiveSessions();
                } else {
                    self.activeSessions = [];
                    self._renderActiveSessions();
                }
            }).catch(function(error) {
                console.error('Error fetching active sessions:', error);
            });
        },
        
        _renderActiveSessions: function() {
            var self = this;
            var $container = this.$('.active_sessions_list');
            $container.empty();
            
            if (this.activeSessions.length === 0) {
                this.$('.no_active_sessions').show();
                return;
            }
            
            this.$('.no_active_sessions').hide();
            
            _.each(this.activeSessions, function(session) {
                var $session = $('<div/>', {
                    'class': 'active_session_item',
                    'data-session-id': session.id
                });
                
                var $header = $('<div/>', {
                    'class': 'session_header',
                    'text': session.name + ' (' + session.partner_name + ')'
                });
                
                var $timer = $('<div/>', {
                    'class': 'session_timer',
                    'data-end-time': session.end_datetime,
                    'html': '<span class="timer_value">Yüklənir...</span>'
                });
                
                $session.append($header).append($timer);
                $container.append($session);
            });
            
            // Initial update of the countdowns
            this._updateCountdowns();
        },
        
        _updateCountdowns: function() {
            var self = this;
            var now = new Date();
            
            this.$('.session_timer').each(function() {
                var $timer = $(this);
                var endTimeStr = $timer.data('end-time');
                var endTime = new Date(endTimeStr);
                
                // Calculate remaining time in seconds
                var timeRemaining = Math.max(0, Math.floor((endTime - now) / 1000));
                
                if (timeRemaining <= 0) {
                    // Session has ended
                    $timer.parent().addClass('session_ended');
                    $timer.find('.timer_value').text('Sessiya Bitdi!');
                } else {
                    // Format remaining time as HH:MM:SS
                    var hours = Math.floor(timeRemaining / 3600);
                    var minutes = Math.floor((timeRemaining % 3600) / 60);
                    var seconds = timeRemaining % 60;
                    
                    var timeStr = (hours > 0 ? hours + ':' : '') + 
                                  (minutes < 10 ? '0' : '') + minutes + ':' + 
                                  (seconds < 10 ? '0' : '') + seconds;
                    
                    $timer.find('.timer_value').text(timeStr);
                    
                    // Add warning class if less than 5 minutes remaining
                    if (timeRemaining < 300) {
                        $timer.parent().addClass('session_ending_soon');
                    } else {
                        $timer.parent().removeClass('session_ending_soon');
                    }
                }
            });
        },
        
        _updateCounterDisplay: function() {
            this.$('.counter_value').text(this.checkCounter);
            this.$('.status_value').text(this.sessionCheckEnabled ? 'Aktiv' : 'Dayandırılıb');
        },
        
        _onSetMaxChecks: function(ev) {
            var value = parseInt(this.$('#max_checks').val(), 10);
            if (!isNaN(value) && value >= 0) {
                this.maxChecks = value;
                this.sessionCheckEnabled = true;
                this.displayNotification({
                    title: 'Maksimum yoxlama sayı yeniləndi',
                    message: 'Yeni limit: ' + (this.maxChecks === 0 ? 'Limitsiz' : this.maxChecks),
                    type: 'info',
                });
                this._updateCounterDisplay();
            }
        },
        
        _onResetChecks: function(ev) {
            this.checkCounter = 0;
            this.sessionCheckEnabled = true;
            this._updateCounterDisplay();
            this.displayNotification({
                title: 'Yoxlama sayı sıfırlandı',
                message: 'Bildiriş sistemi yenidən aktivdir',
                type: 'success',
            });
        },
        
        _onStopChecks: function(ev) {
            this.sessionCheckEnabled = false;
            this._updateCounterDisplay();
            this.displayNotification({
                title: 'Yoxlamalar dayandırıldı',
                message: 'Bildiriş sistemi deaktiv edildi',
                type: 'warning',
            });
        },
        
        _startSessionCheck: function() {
            var self = this;
            
            // Immediately check sessions
            this._checkEndingSessions();
            
            // Setup interval for regular checks
            this.interval = setInterval(function() {
                if (self.sessionCheckEnabled) {
                    self._checkEndingSessions();
                } else {
                    console.log("Session check disabled after " + self.checkCounter + " checks.");
                }
            }, this.notification_check_interval);
        },
        
        _checkEndingSessions: function() {
            var self = this;
            
            // Increment counter
            this.checkCounter++;
            
            // Update counter display
            this._updateCounterDisplay();
            
            // Check if we've reached maximum checks
            if (this.maxChecks > 0 && this.checkCounter > this.maxChecks) {
                this.sessionCheckEnabled = false;
                console.log("Maximum check count reached (" + this.maxChecks + "). Disabling further checks.");
                this._updateCounterDisplay();
                this.displayNotification({
                    title: 'Maksimum yoxlama həddini keçdi',
                    message: 'Limit: ' + this.maxChecks + '. Yenidən başlatmaq üçün "Yoxlamaları Sıfırla" düyməsini basın.',
                    type: 'warning',
                    sticky: true
                });
                return;
            }
            
            // Also refresh active sessions list periodically
            if (this.checkCounter % 5 === 0) { // Refresh every 5 checks
                this._fetchActiveSessions();
            }
            
            // Check if we should throttle checks (not more than once per 30 seconds)
            var now = new Date();
            var timeSinceLastCheck = now - this.lastSessionCheck;
            if (timeSinceLastCheck < 30000) {
                console.log("Throttling check. Last check was " + (timeSinceLastCheck/1000) + " seconds ago.");
                return;
            }
            
            // Record this check time
            this.lastSessionCheck = now;
            
            // Log for debugging
            console.log("Checking for ending sessions. Check #" + this.checkCounter);
            
            this._rpc({
                model: 'badminton.session',
                method: 'get_sessions_ending_soon',
                args: [5, 1], // 5 minutes warning, 1 minute final warning
            }).then(function(result) {
                if (result && result.sessions) {
                    self._processSessionNotifications(result.sessions);
                }
            }).catch(function(error) {
                console.error('Error checking ending sessions:', error);
                self.displayNotification({
                    title: 'Xəta!',
                    message: 'Sessiyaların yoxlanması zamanı xəta baş verdi',
                    type: 'danger',
                });
            });
        },
        
        _processSessionNotifications: function(sessions) {
            var self = this;
            
            sessions.forEach(function(session) {
                // Only notify once for each session at each notification threshold
                var notificationKey = session.id + '_' + session.minutes_remaining;
                
                if (!self.notification_timeouts[notificationKey]) {
                    self.notification_timeouts[notificationKey] = true;
                    
                    // Create notification
                    self._createNotification(session);
                    
                    // Play sound for urgent warnings (less than 1 minute remaining)
                    if (session.minutes_remaining <= 1) {
                        self.audioElement.play();
                    }
                }
            });
        },
        
        _createNotification: function(session) {
            var title, message;
            
            if (session.minutes_remaining <= 1) {
                title = _t("Urgent: Session Ending Now!");
                message = _t("Session for ") + session.partner_name + _t(" is ending now!");
            } else {
                title = _t("Session Ending Soon");
                message = _t("Session for ") + session.partner_name + _t(" will end in ") + 
                    session.minutes_remaining + _t(" minutes");
            }
            
            this.displayNotification({ 
                title: title,
                message: message,
                type: session.minutes_remaining <= 1 ? 'danger' : 'warning',
                sticky: session.minutes_remaining <= 1,
            });
        },
        
        destroy: function() {
            // Clear intervals when widget is destroyed
            if (this.interval) {
                clearInterval(this.interval);
                console.log("Session notification check stopped after " + this.checkCounter + " checks.");
            }
            
            if (this.countdownInterval) {
                clearInterval(this.countdownInterval);
                console.log("Session countdown timer stopped.");
            }
            
            // Reset session check state for next activation
            this.sessionCheckEnabled = false;
            this._super.apply(this, arguments);
        },
        
        // Method to manually reset and restart checks if needed
        resetSessionCheck: function() {
            this.checkCounter = 0;
            this.sessionCheckEnabled = true;
            this._updateCounterDisplay();
            console.log("Session notification checks reset and enabled.");
            return this.displayNotification({
                title: 'Yoxlama sayı sıfırlandı',
                message: 'Bildiriş sistemi yenidən aktivdir',
                type: 'success',
            });
        }
    });
    
    core.action_registry.add('session_notification', SessionNotification);
    
    return SessionNotification;
});
