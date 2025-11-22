# -*- coding: utf-8 -*-

import os
import logging
from logging.handlers import RotatingFileHandler
import traceback
from qbittorrentapi import Client, LoginFailed
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger


# 配置日志
def setup_logging():
    """配置日志系统，限制单个文件最大5MB，保留3个备份文件"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 从环境变量获取日志路径，默认为当前目录下的 qb_auto_cleaner.log
    log_path = os.getenv('LOG_PATH', 'qb_automate.log')

    # 确保日志目录存在
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 文件处理器 - 限制文件大小为5MB，保留3个备份
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 清除现有处理器并添加新处理器
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 记录日志路径信息
    logger.info(f"日志文件路径: {os.path.abspath(log_path)}")


# 初始化日志配置
setup_logging()
logger = logging.getLogger(__name__)


class QBittorrentAutoMate:
    def __init__(self, qb_config):
        self.qb_config = qb_config
        self.qb = None

        # 删除条件配置
        self.ratio_limit = qb_config.get('ratio_limit', 2.0)  # 分享率上限
        self.seeding_time_limit = qb_config.get('seeding_time_limit', 120)  # 做种时间上限（分钟）
        self.exclude_tags = qb_config.get('exclude_tags', [])  # 排除的分类
        self.include_tags = qb_config.get('include_tags', [])  # 只处理这些分类（如果设置了）

    @property
    def connect_qbittorrent(self):
        """连接 qBittorrent"""
        if self.qb_config.get('url') is None or self.qb_config.get('username') is None or self.qb_config.get(
                'password') is None:
            logger.error(f"连接 qBittorrent 失败: 请检查qibittorrent地址,用户名,密码是否已填写")
            return False

        try:
            logger.info(f"连接 qBittorrent: {self.qb_config['url']}:{self.qb_config['port']} 用户名:{self.qb_config['username']}")
            self.qb = Client(host=self.qb_config['url'], port=self.qb_config['port'],
                             username=self.qb_config['username'],
                             password=self.qb_config['password'],
                             VERIFY_WEBUI_CERTIFICATE=False,
                             REQUESTS_ARGS={'timeout': (10, 30)})

            try:
                self.qb.auth_log_in()
                logger.info("成功连接到 qBittorrent:%s" % self.qb.app_version())
            except LoginFailed as e:
                logger.error(f"连接 qBittorrent 失败: {e}")
            return True
        except Exception as e:
            traceback.print_exc()
            logger.error(f"连接 qBittorrent 失败: {e}")
            return False

    def should_delete_torrent(self, torrent):
        """判断是否应该删除种子"""
        # 检查排除分类
        tags = torrent.get('tags', '')
        if tags in self.exclude_tags:
            return False

        # 如果设置了包含分类，只处理这些分类
        if self.include_tags and tags not in self.include_tags:
            return False

        # 获取种子数据
        ratio = torrent['ratio']
        seeding_time = torrent['seeding_time'] / 60  # 转换为分钟

        # 检查是否满足删除条件
        if ratio >= self.ratio_limit or seeding_time >= self.seeding_time_limit:
            logger.info(f"种子满足删除条件: {torrent['name']} - 分享率: {ratio:.2f}, 做种时间: {seeding_time:.1f}分钟")
            return True

        return False

    def get_completed_torrents(self):
        """获取已完成的种子列表"""
        try:
            # 获取所有已经完成的种子
            return self.qb.torrents_info(status_filter='completed')
        except Exception as e:
            logger.error(f"获取种子列表失败: {e}")
            return []

    def delete_torrent(self, torrent, delete_files=False):
        """删除种子"""
        try:
            torrent_name = torrent['name']
            torrent_hash = torrent['hash']

            # 删除种子
            self.qb.torrents_delete(delete_files=delete_files, torrent_hashes=torrent_hash)
            logger.info(f"已删除种子: {torrent_name} (删除文件: {delete_files})")
            return True
        except Exception as e:
            logger.error(f"删除种子失败 {torrent['name']}: {e}")
            return False

    def cleanup_torrents(self):
        """清理满足条件的种子"""
        if not self.qb:
            if not self.connect_qbittorrent:
                return

        logger.info("开始检查种子清理条件...")

        try:
            completed_torrents = self.get_completed_torrents()
            logger.info(f"找到 {len(completed_torrents)} 个已完成的种子")

            deleted_count = 0
            for torrent in completed_torrents:
                if self.should_delete_torrent(torrent):
                    if self.delete_torrent(torrent, delete_files=self.qb_config.get('delete_files', False)):
                        deleted_count += 1

            logger.info(f"清理完成，共删除 {deleted_count} 个种子")

        except Exception as e:
            logger.error(f"清理过程中发生错误: {e}")


def load_config():
    """加载配置"""
    config = {
        'qbittorrent': {
            'url': os.getenv('QB_URL', 'http://localhost'),
            'port': os.getenv('QB_PORT', '8080'),
            'username': os.getenv('QB_USERNAME', 'admin'),
            'password': os.getenv('QB_PASSWORD', 'adminadmin'),
            'ratio_limit': float(os.getenv('RATIO_LIMIT', '2.0')),
            'seeding_time_limit': float(os.getenv('SEEDING_TIME_LIMIT', '120')),  # 3天
            'delete_files': os.getenv('DELETE_FILES', 'false').lower() == 'true',
            'exclude_tags': [cat.strip() for cat in os.getenv('EXCLUDE_TAGS', '').split(',') if
                             cat.strip()],
            'include_tags': [cat.strip() for cat in os.getenv('INCLUDE_TAGS', '').split(',') if
                             cat.strip()],
        },
        'scheduler': {
            'interval_minutes': int(os.getenv('CHECK_INTERVAL', '60')),
        }
    }
    return config


def main():
    """主函数"""
    logger.info("启动 qBittorrent 自动清理服务")

    # 加载配置
    config = load_config()
    qb_config = config['qbittorrent']
    scheduler_config = config['scheduler']

    # 创建清理器实例
    cleaner = QBittorrentAutoMate(qb_config)

    # 测试连接
    if not cleaner.connect_qbittorrent:
        logger.error("初始连接失败，请检查配置")
        return

    # 创建调度器
    scheduler = BlockingScheduler()

    # 添加定时任务
    trigger = IntervalTrigger(minutes=scheduler_config['interval_minutes'])
    scheduler.add_job(
        cleaner.cleanup_torrents,
        trigger=trigger,
        id='qb_cleanup',
        name='qBittorrent 自动清理'
    )

    # 立即执行一次
    logger.info("执行首次清理检查...")
    cleaner.cleanup_torrents()

    logger.info(f"定时清理服务已启动，每 {scheduler_config['interval_minutes']} 分钟检查一次")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("收到停止信号，关闭服务")
    except Exception as e:
        logger.error(f"调度器运行错误: {e}")
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
