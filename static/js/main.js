// Sripad's Bakery - Interactive JavaScript Engine

document.addEventListener('DOMContentLoaded', function () {
    // CSRF Utility
    function getCSRFToken() {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, 10) === 'csrftoken=') {
                    cookieValue = decodeURIComponent(cookie.substring(10));
                    break;
                }
            }
        }
        return cookieValue;
    }
    // Toggle Dark Mode
    const darkModeBtn = document.getElementById('darkModeToggle');
    if (darkModeBtn) {
        darkModeBtn.addEventListener('click', function () {
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDark ? 'enabled' : 'disabled');
            darkModeBtn.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        });
        
        // Restore dark mode
        if (localStorage.getItem('darkMode') === 'enabled') {
            document.body.classList.add('dark-mode');
            darkModeBtn.innerHTML = '<i class="fas fa-sun"></i>';
        }
    }

    // Dynamic Cart Operations (AJAX)
    const addToCartForms = document.querySelectorAll('.add-to-cart-form');
    addToCartForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(form);
            
            fetch('/cart/add/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showToast('Success', data.message, 'success');
                    const cartBadges = document.querySelectorAll('.cart-count-badge');
                    cartBadges.forEach(badge => {
                        badge.textContent = data.cart_count;
                        badge.classList.remove('d-none');
                        badge.classList.remove('animate-pop');
                        void badge.offsetWidth; // trigger reflow to restart animation
                        badge.classList.add('animate-pop');
                    });
                }
            })
            .catch(err => console.error("Cart Error:", err));
        });
    });

    // Toast Alert Helper
    function showToast(title, message, type = 'info') {
        const container = document.getElementById('toastContainer') || createToastContainer();
        const toastId = 'toast-' + Date.now();
        const icon = type === 'success' ? 'fa-check-circle text-success' : type === 'error' ? 'fa-times-circle text-danger' : 'fa-info-circle text-info';
        
        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true" style="border-left: 5px solid ${type === 'success' ? '#2e7d32' : type === 'error' ? '#c62828' : '#0277bd'} !important;">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas ${icon} me-2"></i><strong>${title}</strong>: ${message}
                    </div>
                    <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', toastHTML);
        const toastEl = document.getElementById(toastId);
        const bsToast = new bootstrap.Toast(toastEl, { delay: 4000 });
        bsToast.show();
        toastEl.addEventListener('hidden.bs.toast', function () {
            toastEl.remove();
        });
    }

    function createToastContainer() {
        const div = document.createElement('div');
        div.id = 'toastContainer';
        div.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        div.style.zIndex = '9999';
        document.body.appendChild(div);
        return div;
    }

    // Real-Time Notification Engine (Polling)
    const notificationDropdown = document.getElementById('notificationList');
    const notificationBadge = document.getElementById('notificationCount');
    let knownNotificationIds = null;
    let audioCtx = null;

    function initAudioContext() {
        if (!audioCtx) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (AudioContextClass) {
                audioCtx = new AudioContextClass();
            }
        }
        if (audioCtx && audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
    }

    // Initialize AudioContext on user interaction to bypass autoplay policy
    ['click', 'keydown', 'touchstart'].forEach(eventName => {
        document.addEventListener(eventName, initAudioContext, { once: true });
    });

    function playNotificationSound() {
        try {
            initAudioContext();
            if (!audioCtx) return;
            
            const playTone = (freq, startTime, duration) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, startTime);
                
                gain.gain.setValueAtTime(0, startTime);
                gain.gain.linearRampToValueAtTime(0.2, startTime + 0.03);
                gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
                
                osc.start(startTime);
                osc.stop(startTime + duration);
            };
            
            const now = audioCtx.currentTime;
            playTone(880, now, 0.35);       // A5
            playTone(1320, now + 0.10, 0.5); // E6
        } catch (e) {
            console.warn("Audio playback blocked or failed:", e);
        }
    }
    
    function fetchNotifications() {
        if (!notificationDropdown) return;
        
        fetch('/notifications/api/list/')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const currentIds = data.notifications.map(n => n.id);
                if (knownNotificationIds !== null) {
                    const hasNewNotification = currentIds.some(id => !knownNotificationIds.has(id));
                    if (hasNewNotification) {
                        playNotificationSound();
                    }
                }
                knownNotificationIds = new Set(currentIds);

                if (data.count > 0) {
                    notificationBadge.textContent = data.count;
                    notificationBadge.classList.remove('d-none');
                } else {
                    notificationBadge.classList.add('d-none');
                }
                
                let listHTML = '';
                if (data.notifications.length === 0) {
                    listHTML = '<li class="px-3 py-2 text-center text-muted">No new notifications</li>';
                } else {
                    data.notifications.forEach(n => {
                        listHTML += `
                            <li>
                                <a class="dropdown-item px-3 py-2 border-bottom mark-notification-read" href="${n.link}" data-id="${n.id}">
                                    <div class="d-flex justify-content-between font-weight-bold">
                                        <span>${n.title}</span>
                                        <small class="text-muted">${n.created_at}</small>
                                    </div>
                                    <p class="mb-0 text-truncate text-muted" style="max-width: 250px; font-size: 0.8rem;">${n.message}</p>
                                </a>
                            </li>
                        `;
                    });
                    listHTML += '<li><button class="dropdown-item text-center text-primary font-weight-bold py-2" id="clearAllNotifications">Mark All as Read</button></li>';
                }
                notificationDropdown.innerHTML = listHTML;
                attachNotificationHandlers();
            }
        })
        .catch(err => console.error("Notification Polling Failed:", err));
    }

    function attachNotificationHandlers() {
        const clearBtn = document.getElementById('clearAllNotifications');
        if (clearBtn) {
            clearBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                fetch('/notifications/api/mark-read/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCSRFToken() }
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        fetchNotifications();
                    }
                });
            });
        }
        
        const readLinks = document.querySelectorAll('.mark-notification-read');
        readLinks.forEach(link => {
            link.addEventListener('click', function (e) {
                const nid = link.getAttribute('data-id');
                const href = link.getAttribute('href');
                if (nid) {
                    e.preventDefault();
                    const formData = new FormData();
                    formData.append('id', nid);
                    fetch('/notifications/api/mark-read/', {
                        method: 'POST',
                        headers: { 'X-CSRFToken': getCSRFToken() },
                        body: formData
                    })
                    .then(() => {
                        window.location.href = href;
                    });
                }
            });
        });
    }

    // Start notification polling every 4 seconds if user logged in
    if (notificationDropdown) {
        fetchNotifications();
        setInterval(fetchNotifications, 4000);
    }

    // Dynamic Quantities in Cart Screen
    window.updateCartQty = function (itemId, action) {
        const formData = new FormData();
        formData.append('item_id', itemId);
        formData.append('action', action);
        
        fetch('/cart/update/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Instead of reloading, we can just reload the cart details or reload window for full totals update
                location.reload();
            }
        });
    };

    window.removeFromCart = function (itemId) {
        if (!confirm("Are you sure you want to remove this item?")) return;
        const formData = new FormData();
        formData.append('item_id', itemId);
        
        fetch('/cart/remove/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                location.reload();
            }
        });
    };

    // Live Order Tracking timelines
    const trackingPage = document.getElementById('trackingTimelineContainer');
    if (trackingPage) {
        const orderNumber = trackingPage.getAttribute('data-order-number');
        
        function pollOrderStatus() {
            fetch(`/api/orders/${orderNumber}/`)
            .then(res => {
                if (res.status === 401 || res.status === 403) return null;
                return res.json();
            })
            .then(data => {
                if (data) {
                    updateTrackingUI(data);
                }
            })
            .catch(err => console.error("OrderStatus poll error:", err));
        }

        function updateTrackingUI(order) {
            const statusMap = {
                'placed': 0,
                'payment_received': 1,
                'accepted': 2,
                'preparing': 3,
                'ready': 4,
                'out_for_delivery': 5,
                'delivered': 6
            };
            
            const currentIdx = statusMap[order.order_status];
            const timelineItems = document.querySelectorAll('.timeline-item');
            
            timelineItems.forEach((item, idx) => {
                item.classList.remove('active', 'completed');
                const itemStatus = item.getAttribute('data-status');
                const itemIdx = statusMap[itemStatus];
                
                if (itemIdx < currentIdx) {
                    item.classList.add('completed');
                } else if (itemIdx === currentIdx) {
                    item.classList.add('active');
                }
            });

            // Update pricing elements dynamically if they exist
            const chargeLabel = document.getElementById('trackingDeliveryCharges');
            const grandTotalLabel = document.getElementById('trackingGrandTotal');
            const remainingAmountLabel = document.getElementById('trackingRemainingAmount');
            
            if (chargeLabel) {
                if (order.delivery_type === 'pickup') {
                    chargeLabel.innerHTML = '<span class="text-success font-weight-semibold">Free (Self Pickup)</span>';
                } else {
                    const charges = parseFloat(order.delivery_charges);
                    if (charges > 0) {
                        chargeLabel.textContent = '₹' + charges.toFixed(2);
                    } else {
                        chargeLabel.innerHTML = '<span class="text-warning-emphasis font-weight-bold">TBD by Bakery</span>';
                    }
                }
            }
            if (grandTotalLabel) {
                grandTotalLabel.textContent = '₹' + parseFloat(order.grand_total).toFixed(2);
            }
            if (remainingAmountLabel) {
                remainingAmountLabel.textContent = '₹' + parseFloat(order.remaining_amount).toFixed(2);
            }

            // If order cancelled, show warning alert and color red
            if (order.order_status === 'cancelled') {
                const alertArea = document.getElementById('trackingCancellationAlert');
                if (alertArea) {
                    alertArea.classList.remove('d-none');
                    document.getElementById('cancellationReasonText').textContent = order.cancellation_reason || 'Not specified';
                }
            }
            
            // If delivered, display feedback button
            if (order.order_status === 'delivered') {
                const feedbackSection = document.getElementById('deliveredFeedbackSection');
                if (feedbackSection) {
                    feedbackSection.classList.remove('d-none');
                }
            }
        }

        // Poll order status every 3 seconds
        setInterval(pollOrderStatus, 3000);
    }

    // Live Chat system
    const chatBox = document.getElementById('chatMessagesContainer');
    if (chatBox) {
        const orderNumber = chatBox.getAttribute('data-order-number');
        const chatForm = document.getElementById('chatSendForm');
        let lastMessageId = 0;
        
        function scrollChatToBottom() {
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function pollChatMessages() {
            fetch(`/chat/api/messages/${orderNumber}/?last_id=${lastMessageId}`)
            .then(res => res.json())
            .then(data => {
                if (data.success && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        const isMe = msg.is_me;
                        const bubbleHTML = `
                            <div class="d-flex flex-column ${isMe ? 'align-items-end' : 'align-items-start'} mb-3">
                                <div class="message-bubble ${isMe ? 'me' : 'other'}">
                                    ${msg.message ? `<p class="mb-1">${msg.message}</p>` : ''}
                                    ${msg.image_url ? `<img src="${msg.image_url}" class="img-fluid rounded border mb-1" style="max-height: 150px; cursor: pointer;" onclick="window.open('${msg.image_url}')">` : ''}
                                </div>
                                <small class="text-muted" style="font-size: 0.7rem; margin: -8px 8px 0 8px;">
                                    ${isMe ? 'You' : msg.sender_username} • ${msg.created_at}
                                </small>
                            </div>
                        `;
                        chatBox.insertAdjacentHTML('beforeend', bubbleHTML);
                        lastMessageId = Math.max(lastMessageId, msg.id);
                    });
                    scrollChatToBottom();
                }
            })
            .catch(err => console.error("Chat polling error:", err));
        }

        if (chatForm) {
            chatForm.addEventListener('submit', function (e) {
                e.preventDefault();
                const formData = new FormData(chatForm);
                const textInput = document.getElementById('chatTextInput');
                const imageInput = document.getElementById('chatImageInput');
                
                if (!textInput.value.trim() && !imageInput.files.length) return;
                
                fetch(`/chat/api/send/${orderNumber}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCSRFToken() },
                    body: formData
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        textInput.value = '';
                        imageInput.value = '';
                        // Poll immediately to show sent message
                        pollChatMessages();
                    }
                })
                .catch(err => console.error("Error sending message:", err));
            });
        }

        // Start chat polling loop every 2 seconds
        pollChatMessages();
        setInterval(pollChatMessages, 2000);
    }
});
