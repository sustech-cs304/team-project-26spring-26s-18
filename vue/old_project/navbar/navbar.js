function initNavbarActive() {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function (e) {
      document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('navbar-active'));
      this.classList.add('navbar-active');
      console.log('导航链接被点击:', this.getAttribute('href'));
    });
  });
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') && window.location.pathname.endsWith(link.getAttribute('href').split('/').pop())) {
      console.log('匹配当前页面的导航链接:', link.getAttribute('href').split('/').pop());
      link.classList.add('navbar-active');
    }
  });
  // 动态设置用户信息
  var userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      var user = JSON.parse(userStr);
      // 设置用户名
      var usernameSpan = document.querySelector('.username');
      if (usernameSpan) {
        usernameSpan.textContent = user.userName || '暂无用户名';
      }
      // 设置头像
      var userIcon = document.querySelector('.navbar-user-icon');
      if (userIcon && user.avatarURL) {
        userIcon.src = user.avatarURL;
      }
    } catch (e) {
      // 解析失败不处理
    }
  }
  // 提示框函数
  function showToast(msg, duration = 2000) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.style.display = 'block';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.style.display = 'none';
    }, duration);
  }
  // 用户中心点击跳转判断
  var userInfoLink = document.querySelector('.navbar-user-info');
  if (userInfoLink) {
    userInfoLink.addEventListener('click', function (e) {
      var user = localStorage.getItem('user');
      if (!user) {
        e.preventDefault();
        showToast('请先登录！');
        setTimeout(function () {
          window.location.href = '../htmls/login.html';
        }, 1200);
      }
    });
  }
  // 创作中心点击跳转判断
  var createCenterLink = document.querySelector('.navbar-create-center');
  if (createCenterLink) {
    createCenterLink.addEventListener('click', function (e) {
      var user = localStorage.getItem('user');
      if (!user) {
        e.preventDefault();
        showToast('请先登录！');
        setTimeout(function () {
          window.location.href = '../htmls/login.html';
        }, 1200);
      }
    });
  }
}