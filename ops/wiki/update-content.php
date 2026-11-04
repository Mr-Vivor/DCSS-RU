<?php
/** Update reviewed wiki blocks, preserving editor text and reporting conflicts. */
use MediaWiki\CommentStore\CommentStoreComment;
use MediaWiki\Content\ContentHandler;
use MediaWiki\Deferred\DeferredUpdates;
use MediaWiki\MediaWikiServices;
use MediaWiki\Title\Title;

require_once '/srv/dcss-wiki/current/maintenance/Maintenance.php';

class UpdateDcssWiki extends Maintenance {
    public function __construct() {
        parent::__construct();
        $this->addDescription( 'Import reviewed DCSS wiki content without overwriting editor changes.' );
        $this->addArg( 'payload', 'Path to generated pages.json' );
        $this->addOption( 'initial', 'Replace the installer-created main page only.' );
    }

    public function execute() {
        $payload = json_decode( file_get_contents( $this->getArg( 0 ) ), true, 512, JSON_THROW_ON_ERROR );
        if ( ( $payload['schema'] ?? null ) !== 1 ) {
            $this->fatalError( 'Unsupported wiki payload.' );
        }
        $statePath = '/srv/dcss-wiki/shared/import-state.json';
        $lock = fopen( '/srv/dcss-wiki/shared/import.lock', 'c' );
        if ( !$lock || !flock( $lock, LOCK_EX ) ) {
            $this->fatalError( 'Cannot lock wiki content updates.' );
        }
        $state = is_file( $statePath ) ? json_decode( file_get_contents( $statePath ), true, 512, JSON_THROW_ON_ERROR ) : [];
        $services = MediaWikiServices::getInstance();
        $user = $services->getUserFactory()->newFromName( 'Vivor' );
        if ( !$user || !$user->getId() ) {
            $this->fatalError( 'The configured wiki administrator does not exist.' );
        }
        $counts = [ 'saved' => 0, 'unchanged' => 0, 'conflicts' => 0 ];
        $conflicts = [];
        foreach ( $payload['pages'] as $name => $entry ) {
            $title = Title::newFromText( $name );
            if ( !$title || $title->isExternal() ) {
                throw new RuntimeException( 'Invalid generated title: ' . $name );
            }
            $page = $services->getWikiPageFactory()->newFromTitle( $title );
            $content = $page->getContent();
            $old = $content ? $content->serialize() : '';
            $id = substr( hash( 'sha256', $entry['key'] ), 0, 20 );
            $css = ( $entry['kind'] === 'css' );
            $begin = $css ? "/* DCSS-AUTO-BEGIN:$id */" : "<!-- DCSS-AUTO-BEGIN:$id -->";
            $end = $css ? "/* DCSS-AUTO-END:$id */" : "<!-- DCSS-AUTO-END:$id -->";
            // Redirect magic words must remain at the beginning of the page.
            if ( in_array( $entry['kind'], [ 'redirect', 'message' ], true ) ) {
                $new = $entry['text'] . ( $entry['kind'] === 'redirect' ? "\n" . $begin . $end : '' );
                if ( $old !== '' && $old !== $new && ( $state[$name] ?? null ) !== hash( 'sha256', $old ) ) {
                    $conflicts[] = $name;
                    $counts['conflicts']++;
                    continue;
                }
                $digest = hash( 'sha256', $new );
            } else {
                $block = $begin . "\n" . $entry['text'] . "\n" . $end;
                $first = strpos( $old, $begin );
                $last = strpos( $old, $end );
                if ( $old === '' || ( $this->hasOption( 'initial' ) && $name === 'Заглавная страница' && $first === false ) ) {
                    $new = $block;
                } elseif ( $first !== false && $last !== false && $last >= $first ) {
                    $existing = substr( $old, $first, $last + strlen( $end ) - $first );
                    $expected = $state[$name] ?? null;
                    if ( $existing !== $block && $expected !== hash( 'sha256', $existing ) ) {
                        $conflicts[] = $name;
                        $counts['conflicts']++;
                        continue;
                    }
                    $new = substr( $old, 0, $first ) . $block . substr( $old, $last + strlen( $end ) );
                } else {
                    $conflicts[] = $name;
                    $counts['conflicts']++;
                    continue;
                }
                $digest = hash( 'sha256', $block );
            }
            if ( $old === $new ) {
                $counts['unchanged']++;
            } else {
                $updater = $page->newPageUpdater( $user );
                $updater->setContent( 'main', ContentHandler::makeContent( $new, $title ) );
                $revision = $updater->saveRevision( CommentStoreComment::newUnsavedComment( 'Общие данные русского форка 0.35-a0; источники указаны на странице' ), EDIT_SUPPRESS_RC );
                if ( !$revision ) {
                    throw new RuntimeException( 'Could not save wiki page: ' . $name );
                }
                $counts['saved']++;
            }
            $state[$name] = $digest;
            if ( ( $counts['saved'] + $counts['unchanged'] ) % 50 === 0 ) {
                DeferredUpdates::doUpdates();
            }
            if ( ( $counts['saved'] + $counts['unchanged'] ) % 200 === 0 ) {
                file_put_contents( $statePath . '.tmp', json_encode( $state, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT ) );
                rename( $statePath . '.tmp', $statePath );
                $this->output( json_encode( $counts ) . "\n" );
            }
        }
        file_put_contents( $statePath . '.tmp', json_encode( $state, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT ) );
        rename( $statePath . '.tmp', $statePath );
        file_put_contents( '/srv/dcss-wiki/shared/import-conflicts.json', json_encode( $conflicts, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT ) );
        $this->output( json_encode( $counts ) . "\n" );
    }
}

$maintClass = UpdateDcssWiki::class;
require_once RUN_MAINTENANCE_IF_MAIN;
